import datetime as dt
import json
import re
import typing
from string import Template

from temporalio import workflow

SELECT_QUERY_TEMPLATE = Template(
    """
    SELECT $fields
    FROM events
    WHERE
        -- These 'timestamp' checks are a heuristic to exploit the sort key.
        -- Ideally, we need a schema that serves our needs, i.e. with a sort key on the _timestamp field used for batch exports.
        -- As a side-effect, this heuristic will discard historical loads older than 2 days.
        timestamp >= toDateTime({data_interval_start}, 'UTC') - INTERVAL 2 DAY
        AND timestamp < toDateTime({data_interval_end}, 'UTC') + INTERVAL 1 DAY
        AND COALESCE(inserted_at, _timestamp) >= toDateTime64({data_interval_start}, 6, 'UTC')
        AND COALESCE(inserted_at, _timestamp) < toDateTime64({data_interval_end}, 6, 'UTC')
        AND team_id = {team_id}
    $order_by
    $format
    """
)


async def get_rows_count(client, team_id: int, interval_start: str, interval_end: str) -> int:
    data_interval_start_ch = dt.datetime.fromisoformat(interval_start).strftime("%Y-%m-%d %H:%M:%S")
    data_interval_end_ch = dt.datetime.fromisoformat(interval_end).strftime("%Y-%m-%d %H:%M:%S")
    query = SELECT_QUERY_TEMPLATE.substitute(
        fields="count(DISTINCT event, cityHash64(distinct_id), cityHash64(uuid)) as count", order_by="", format=""
    )
    count = await client.read_query(
        query,
        query_parameters={
            "team_id": team_id,
            "data_interval_start": data_interval_start_ch,
            "data_interval_end": data_interval_end_ch,
        },
    )

    if count is None or len(count) == 0:
        raise ValueError("Unexpected result from ClickHouse: `None` returned for count query")

    return int(count)


FIELDS = """
DISTINCT ON (event, cityHash64(distinct_id), cityHash64(uuid))
toString(uuid) as uuid,
team_id,
timestamp,
inserted_at,
created_at,
event,
properties,
-- Point in time identity fields
toString(distinct_id) as distinct_id,
toString(person_id) as person_id,
person_properties,
-- Autocapture fields
elements_chain
"""


def get_results_iterator(
    client, team_id: int, interval_start: str, interval_end: str
) -> typing.Generator[dict[str, typing.Any], None, None]:
    data_interval_start_ch = dt.datetime.fromisoformat(interval_start).strftime("%Y-%m-%d %H:%M:%S")
    data_interval_end_ch = dt.datetime.fromisoformat(interval_end).strftime("%Y-%m-%d %H:%M:%S")
    query = SELECT_QUERY_TEMPLATE.substitute(
        fields=FIELDS,
        order_by="ORDER BY inserted_at",
        format="FORMAT ArrowStream",
    )

    for batch in client.stream_query_as_arrow(
        query,
        query_parameters={
            "team_id": team_id,
            "data_interval_start": data_interval_start_ch,
            "data_interval_end": data_interval_end_ch,
        },
    ):
        yield from iter_batch_records(batch)


def iter_batch_records(batch) -> typing.Generator[dict[str, typing.Any], None, None]:
    """Iterate over records of a batch.

    During iteration, we yield dictionaries with all fields used by PostHog BatchExports.

    Args:
        batch: A record batch of rows.
    """

    for record in batch.to_pylist():
        properties = record.get("properties")
        person_properties = record.get("person_properties")
        properties = json.loads(properties) if properties else None

        elements = elements_chain_to_elements(record.get("elements_chain").decode())

        record = {
            "created_at": record.get("created_at").strftime("%Y-%m-%d %H:%M:%S.%f"),
            "distinct_id": record.get("distinct_id").decode(),
            "elements": elements,
            "elements_chain": record.get("elements_chain").decode(),
            "event": record.get("event").decode(),
            "inserted_at": record.get("inserted_at").strftime("%Y-%m-%d %H:%M:%S.%f")
            if record.get("inserted_at")
            else None,
            "ip": properties.get("$ip", None) if properties else None,
            "person_id": record.get("person_id").decode(),
            "person_properties": json.loads(person_properties) if person_properties else None,
            "set": properties.get("$set", None) if properties else None,
            "set_once": properties.get("$set_once", None) if properties else None,
            "properties": properties,
            "site_url": properties.get("$current_url", None) if properties else None,
            "team_id": record.get("team_id"),
            "timestamp": record.get("timestamp").strftime("%Y-%m-%d %H:%M:%S.%f"),
            "uuid": record.get("uuid").decode(),
        }

        yield record


def get_data_interval(interval: str, data_interval_end: str | None) -> tuple[dt.datetime, dt.datetime]:
    """Return the start and end of an export's data interval.

    Args:
        interval: The interval of the BatchExport associated with this Workflow.
        data_interval_end: The optional end of the BatchExport period. If not included, we will
            attempt to extract it from Temporal SearchAttributes.

    Raises:
        TypeError: If when trying to obtain the data interval end we run into non-str types.
        ValueError: If passing an unsupported interval value.

    Returns:
        A tuple of two dt.datetime indicating start and end of the data_interval.
    """
    data_interval_end_str = data_interval_end

    if not data_interval_end_str:
        data_interval_end_search_attr = workflow.info().search_attributes.get("TemporalScheduledStartTime")

        # These two if-checks are a bit pedantic, but Temporal SDK is heavily typed.
        # So, they exist to make mypy happy.
        if data_interval_end_search_attr is None:
            msg = (
                "Expected 'TemporalScheduledStartTime' of type 'list[str]' or 'list[datetime], found 'NoneType'."
                "This should be set by the Temporal Schedule unless triggering workflow manually."
                "In the latter case, ensure 'S3BatchExportInputs.data_interval_end' is set."
            )
            raise TypeError(msg)

        # Failing here would perhaps be a bug in Temporal.
        if isinstance(data_interval_end_search_attr[0], str):
            data_interval_end_str = data_interval_end_search_attr[0]
            data_interval_end_dt = dt.datetime.fromisoformat(data_interval_end_str)

        elif isinstance(data_interval_end_search_attr[0], dt.datetime):
            data_interval_end_dt = data_interval_end_search_attr[0]

        else:
            msg = (
                f"Expected search attribute to be of type 'str' or 'datetime' found '{data_interval_end_search_attr[0]}' "
                f"of type '{type(data_interval_end_search_attr[0])}'."
            )
            raise TypeError(msg)
    else:
        data_interval_end_dt = dt.datetime.fromisoformat(data_interval_end_str)

    if interval == "hour":
        data_interval_start_dt = data_interval_end_dt - dt.timedelta(hours=1)
    elif interval == "day":
        data_interval_start_dt = data_interval_end_dt - dt.timedelta(days=1)
    else:
        raise ValueError(f"Unsupported interval: '{interval}'")

    return (data_interval_start_dt, data_interval_end_dt)


def elements_chain_to_elements(elements_chain: str) -> list[dict]:
    """Parses the elements_chain string into a list of dict.

    The output format is built by observing how it is read by
    https://github.com/PostHog/posthog/blob/master/plugin-server/src/utils/db/elements-chain.ts
    This is not the same as the chain_to_elements function in posthog.models.elements.
    """
    elements = []

    split_chain_regex = re.compile(r'(?:[^\s;"]|"(?:\\.|[^"])*")+')
    split_class_attributes_regex = re.compile(r"(.*?)($|:([a-zA-Z\-_0-9]*=.*))", flags=re.MULTILINE)
    parse_attributes_regex = re.compile(r'((.*?)="(.*?[^\\])")')

    elements_chain = elements_chain.replace("\n", "")

    for match in re.finditer(split_chain_regex, elements_chain):
        class_attributes = re.search(split_class_attributes_regex, match.group(0))

        attributes = {}
        if class_attributes is not None and class_attributes.group(3):
            try:
                attributes = {m[2]: m[3] for m in re.finditer(parse_attributes_regex, class_attributes.group(3))}
            except IndexError:
                pass

        element = {}

        if class_attributes is not None and class_attributes.group(1):
            try:
                tag_and_class = class_attributes.group(1).split(".")
            except IndexError:
                pass
            else:
                element["tag_name"] = tag_and_class.pop(0)
                if len(tag_and_class) > 0:
                    element["attr__class"] = tag_and_class

        for key, value in attributes.items():
            match key:
                case "href":
                    element["attr__href"] = value
                case "nth-child":
                    element["nth_child"] = int(value)
                case "nth-of-type":
                    element["nth_of_type"] = int(value)
                case "text":
                    element["$el_text"] = value
                case "attr_id":
                    element["attr__id"] = value
                case k:
                    element[k] = value

        elements.append(element)

    return elements
