from dataclasses import dataclass
import re
from typing import Dict

from clickhouse_driver.errors import ServerException

from posthog.exceptions import EstimatedQueryExecutionTimeTooLong


class InternalCHQueryError(ServerException):
    code_name: str

    def __init__(self, message, *, code=None, nested=None, code_name):
        self.code_name = code_name
        super().__init__(message, code, nested)


class ExposedCHQueryError(InternalCHQueryError):
    def __str__(self) -> str:
        message: str = self.message
        try:
            start_index = message.index("DB::Exception:") + len("DB::Exception:")
        except ValueError:
            start_index = 0
        try:
            end_index = message.index("Stack trace:")
        except ValueError:
            end_index = len(message)
        return self.message[start_index:end_index].strip()


@dataclass
class ErrorCodeMeta:
    name: str
    user_safe: bool | str = False
    """Whether this error code is safe to show to the user and couldn't be caught at HogQL level.
    If a string is set, it will be used as the error message instead of the ClickHouse one.
    """


def wrap_query_error(err: Exception) -> Exception:
    "Beautifies clickhouse client errors, using custom error classes for every code"
    if not isinstance(err, ServerException):
        return err

    # Return a 512 error for queries which would time out
    match = re.search(r"Estimated query execution time \(.* seconds\) is too long.", err.message)
    if match:
        return EstimatedQueryExecutionTimeTooLong(detail=match.group(0))

    # :TRICKY: Return a custom class for every code by looking up the short name and creating a class dynamically.
    if hasattr(err, "code"):
        meta = look_up_error_code_meta(err)
        name = f"CHQueryError{meta.name.replace('_', ' ').title().replace(' ', '')}"
        processed_error_class = ExposedCHQueryError if meta.user_safe else InternalCHQueryError
        message = meta.user_safe if isinstance(meta.user_safe, str) else err.message
        return type(name, (processed_error_class,), {})(message, code=err.code, code_name=meta.name.lower())
    return err


def look_up_error_code_meta(error: ServerException) -> ErrorCodeMeta:
    code = getattr(error, "code", None)
    if code is None or code not in CLICKHOUSE_ERROR_CODE_LOOKUP:
        return CLICKHOUSE_UNKNOWN_EXCEPTION
    return CLICKHOUSE_ERROR_CODE_LOOKUP[code]


#
# From https://github.com/ClickHouse/ClickHouse/blob/23.11/src/Common/ErrorCodes.cpp#L16-L596
#
# Please keep this list up to date at each ClickHouse upgrade.
#
# You can fetch and print an updated list of error codes with something like:
#
# import re
# import requests
#
# output = {}
# resp = requests.get("https://raw.githubusercontent.com/ClickHouse/ClickHouse/23.11/src/Common/ErrorCodes.cpp")
# for line in resp.text.split("\n"):
#     result = re.search(r"^M\(([0-9]+), (\S+)\).*$", line.strip())
#     if result is not None:
#         output[int(result.group(1))] = result.group(2)
# print("{")
# for key, value in dict(sorted(output.items())).items():
#     print(f"    {key}: ErrorCodeMeta('{value}'),")
# print("}")
#
CLICKHOUSE_UNKNOWN_EXCEPTION = ErrorCodeMeta("UNKNOWN_EXCEPTION")
CLICKHOUSE_ERROR_CODE_LOOKUP: Dict[int, ErrorCodeMeta] = {
    0: ErrorCodeMeta("OK"),
    1: ErrorCodeMeta("UNSUPPORTED_METHOD"),
    2: ErrorCodeMeta("UNSUPPORTED_PARAMETER"),
    3: ErrorCodeMeta("UNEXPECTED_END_OF_FILE"),
    4: ErrorCodeMeta("EXPECTED_END_OF_FILE"),
    6: ErrorCodeMeta("CANNOT_PARSE_TEXT"),
    7: ErrorCodeMeta("INCORRECT_NUMBER_OF_COLUMNS"),
    8: ErrorCodeMeta("THERE_IS_NO_COLUMN"),
    9: ErrorCodeMeta("SIZES_OF_COLUMNS_DOESNT_MATCH"),
    10: ErrorCodeMeta("NOT_FOUND_COLUMN_IN_BLOCK"),
    11: ErrorCodeMeta("POSITION_OUT_OF_BOUND"),
    12: ErrorCodeMeta("PARAMETER_OUT_OF_BOUND"),
    13: ErrorCodeMeta("SIZES_OF_COLUMNS_IN_TUPLE_DOESNT_MATCH"),
    15: ErrorCodeMeta("DUPLICATE_COLUMN"),
    16: ErrorCodeMeta("NO_SUCH_COLUMN_IN_TABLE"),
    19: ErrorCodeMeta("SIZE_OF_FIXED_STRING_DOESNT_MATCH"),
    20: ErrorCodeMeta("NUMBER_OF_COLUMNS_DOESNT_MATCH"),
    23: ErrorCodeMeta("CANNOT_READ_FROM_ISTREAM"),
    24: ErrorCodeMeta("CANNOT_WRITE_TO_OSTREAM"),
    25: ErrorCodeMeta("CANNOT_PARSE_ESCAPE_SEQUENCE"),
    26: ErrorCodeMeta("CANNOT_PARSE_QUOTED_STRING"),
    27: ErrorCodeMeta("CANNOT_PARSE_INPUT_ASSERTION_FAILED"),
    28: ErrorCodeMeta("CANNOT_PRINT_FLOAT_OR_DOUBLE_NUMBER"),
    32: ErrorCodeMeta("ATTEMPT_TO_READ_AFTER_EOF"),
    33: ErrorCodeMeta("CANNOT_READ_ALL_DATA"),
    34: ErrorCodeMeta("TOO_MANY_ARGUMENTS_FOR_FUNCTION"),
    35: ErrorCodeMeta("TOO_FEW_ARGUMENTS_FOR_FUNCTION"),
    36: ErrorCodeMeta("BAD_ARGUMENTS"),
    37: ErrorCodeMeta("UNKNOWN_ELEMENT_IN_AST"),
    38: ErrorCodeMeta("CANNOT_PARSE_DATE"),
    39: ErrorCodeMeta("TOO_LARGE_SIZE_COMPRESSED"),
    40: ErrorCodeMeta("CHECKSUM_DOESNT_MATCH"),
    41: ErrorCodeMeta("CANNOT_PARSE_DATETIME"),
    42: ErrorCodeMeta("NUMBER_OF_ARGUMENTS_DOESNT_MATCH"),
    43: ErrorCodeMeta("ILLEGAL_TYPE_OF_ARGUMENT"),
    44: ErrorCodeMeta("ILLEGAL_COLUMN"),
    46: ErrorCodeMeta("UNKNOWN_FUNCTION"),
    47: ErrorCodeMeta("UNKNOWN_IDENTIFIER"),
    48: ErrorCodeMeta("NOT_IMPLEMENTED"),
    49: ErrorCodeMeta("LOGICAL_ERROR"),
    50: ErrorCodeMeta("UNKNOWN_TYPE"),
    51: ErrorCodeMeta("EMPTY_LIST_OF_COLUMNS_QUERIED"),
    52: ErrorCodeMeta("COLUMN_QUERIED_MORE_THAN_ONCE"),
    53: ErrorCodeMeta("TYPE_MISMATCH"),
    55: ErrorCodeMeta("STORAGE_REQUIRES_PARAMETER"),
    56: ErrorCodeMeta("UNKNOWN_STORAGE"),
    57: ErrorCodeMeta("TABLE_ALREADY_EXISTS"),
    58: ErrorCodeMeta("TABLE_METADATA_ALREADY_EXISTS"),
    59: ErrorCodeMeta("ILLEGAL_TYPE_OF_COLUMN_FOR_FILTER"),
    60: ErrorCodeMeta("UNKNOWN_TABLE"),
    62: ErrorCodeMeta("SYNTAX_ERROR"),
    63: ErrorCodeMeta("UNKNOWN_AGGREGATE_FUNCTION"),
    68: ErrorCodeMeta("CANNOT_GET_SIZE_OF_FIELD"),
    69: ErrorCodeMeta("ARGUMENT_OUT_OF_BOUND"),
    70: ErrorCodeMeta("CANNOT_CONVERT_TYPE"),
    71: ErrorCodeMeta("CANNOT_WRITE_AFTER_END_OF_BUFFER"),
    72: ErrorCodeMeta("CANNOT_PARSE_NUMBER"),
    73: ErrorCodeMeta("UNKNOWN_FORMAT"),
    74: ErrorCodeMeta("CANNOT_READ_FROM_FILE_DESCRIPTOR"),
    75: ErrorCodeMeta("CANNOT_WRITE_TO_FILE_DESCRIPTOR"),
    76: ErrorCodeMeta("CANNOT_OPEN_FILE"),
    77: ErrorCodeMeta("CANNOT_CLOSE_FILE"),
    78: ErrorCodeMeta("UNKNOWN_TYPE_OF_QUERY"),
    79: ErrorCodeMeta("INCORRECT_FILE_NAME"),
    80: ErrorCodeMeta("INCORRECT_QUERY"),
    81: ErrorCodeMeta("UNKNOWN_DATABASE"),
    82: ErrorCodeMeta("DATABASE_ALREADY_EXISTS"),
    83: ErrorCodeMeta("DIRECTORY_DOESNT_EXIST"),
    84: ErrorCodeMeta("DIRECTORY_ALREADY_EXISTS"),
    85: ErrorCodeMeta("FORMAT_IS_NOT_SUITABLE_FOR_INPUT"),
    86: ErrorCodeMeta("RECEIVED_ERROR_FROM_REMOTE_IO_SERVER"),
    87: ErrorCodeMeta("CANNOT_SEEK_THROUGH_FILE"),
    88: ErrorCodeMeta("CANNOT_TRUNCATE_FILE"),
    89: ErrorCodeMeta("UNKNOWN_COMPRESSION_METHOD"),
    90: ErrorCodeMeta("EMPTY_LIST_OF_COLUMNS_PASSED"),
    91: ErrorCodeMeta("SIZES_OF_MARKS_FILES_ARE_INCONSISTENT"),
    92: ErrorCodeMeta("EMPTY_DATA_PASSED"),
    93: ErrorCodeMeta("UNKNOWN_AGGREGATED_DATA_VARIANT"),
    94: ErrorCodeMeta("CANNOT_MERGE_DIFFERENT_AGGREGATED_DATA_VARIANTS"),
    95: ErrorCodeMeta("CANNOT_READ_FROM_SOCKET"),
    96: ErrorCodeMeta("CANNOT_WRITE_TO_SOCKET"),
    99: ErrorCodeMeta("UNKNOWN_PACKET_FROM_CLIENT"),
    100: ErrorCodeMeta("UNKNOWN_PACKET_FROM_SERVER"),
    101: ErrorCodeMeta("UNEXPECTED_PACKET_FROM_CLIENT"),
    102: ErrorCodeMeta("UNEXPECTED_PACKET_FROM_SERVER"),
    104: ErrorCodeMeta("TOO_SMALL_BUFFER_SIZE"),
    107: ErrorCodeMeta("FILE_DOESNT_EXIST"),
    108: ErrorCodeMeta("NO_DATA_TO_INSERT"),
    109: ErrorCodeMeta("CANNOT_BLOCK_SIGNAL"),
    110: ErrorCodeMeta("CANNOT_UNBLOCK_SIGNAL"),
    111: ErrorCodeMeta("CANNOT_MANIPULATE_SIGSET"),
    112: ErrorCodeMeta("CANNOT_WAIT_FOR_SIGNAL"),
    113: ErrorCodeMeta("THERE_IS_NO_SESSION"),
    114: ErrorCodeMeta("CANNOT_CLOCK_GETTIME"),
    115: ErrorCodeMeta("UNKNOWN_SETTING"),
    116: ErrorCodeMeta("THERE_IS_NO_DEFAULT_VALUE"),
    117: ErrorCodeMeta("INCORRECT_DATA"),
    119: ErrorCodeMeta("ENGINE_REQUIRED"),
    120: ErrorCodeMeta("CANNOT_INSERT_VALUE_OF_DIFFERENT_SIZE_INTO_TUPLE"),
    121: ErrorCodeMeta("UNSUPPORTED_JOIN_KEYS"),
    122: ErrorCodeMeta("INCOMPATIBLE_COLUMNS"),
    123: ErrorCodeMeta("UNKNOWN_TYPE_OF_AST_NODE"),
    124: ErrorCodeMeta("INCORRECT_ELEMENT_OF_SET"),
    125: ErrorCodeMeta("INCORRECT_RESULT_OF_SCALAR_SUBQUERY"),
    127: ErrorCodeMeta("ILLEGAL_INDEX"),
    128: ErrorCodeMeta("TOO_LARGE_ARRAY_SIZE"),
    129: ErrorCodeMeta("FUNCTION_IS_SPECIAL"),
    130: ErrorCodeMeta("CANNOT_READ_ARRAY_FROM_TEXT"),
    131: ErrorCodeMeta("TOO_LARGE_STRING_SIZE"),
    133: ErrorCodeMeta("AGGREGATE_FUNCTION_DOESNT_ALLOW_PARAMETERS"),
    134: ErrorCodeMeta("PARAMETERS_TO_AGGREGATE_FUNCTIONS_MUST_BE_LITERALS"),
    135: ErrorCodeMeta("ZERO_ARRAY_OR_TUPLE_INDEX"),
    137: ErrorCodeMeta("UNKNOWN_ELEMENT_IN_CONFIG"),
    138: ErrorCodeMeta("EXCESSIVE_ELEMENT_IN_CONFIG"),
    139: ErrorCodeMeta("NO_ELEMENTS_IN_CONFIG"),
    141: ErrorCodeMeta("SAMPLING_NOT_SUPPORTED"),
    142: ErrorCodeMeta("NOT_FOUND_NODE"),
    145: ErrorCodeMeta("UNKNOWN_OVERFLOW_MODE"),
    152: ErrorCodeMeta("UNKNOWN_DIRECTION_OF_SORTING"),
    153: ErrorCodeMeta("ILLEGAL_DIVISION"),
    156: ErrorCodeMeta("DICTIONARIES_WAS_NOT_LOADED"),
    158: ErrorCodeMeta("TOO_MANY_ROWS"),
    159: ErrorCodeMeta("TIMEOUT_EXCEEDED"),
    160: ErrorCodeMeta("TOO_SLOW"),
    161: ErrorCodeMeta("TOO_MANY_COLUMNS"),
    162: ErrorCodeMeta("TOO_DEEP_SUBQUERIES"),
    164: ErrorCodeMeta("READONLY"),
    165: ErrorCodeMeta("TOO_MANY_TEMPORARY_COLUMNS"),
    166: ErrorCodeMeta("TOO_MANY_TEMPORARY_NON_CONST_COLUMNS"),
    167: ErrorCodeMeta("TOO_DEEP_AST"),
    168: ErrorCodeMeta("TOO_BIG_AST"),
    169: ErrorCodeMeta("BAD_TYPE_OF_FIELD"),
    170: ErrorCodeMeta("BAD_GET"),
    172: ErrorCodeMeta("CANNOT_CREATE_DIRECTORY"),
    173: ErrorCodeMeta("CANNOT_ALLOCATE_MEMORY"),
    174: ErrorCodeMeta("CYCLIC_ALIASES"),
    179: ErrorCodeMeta("MULTIPLE_EXPRESSIONS_FOR_ALIAS"),
    180: ErrorCodeMeta("THERE_IS_NO_PROFILE"),
    181: ErrorCodeMeta("ILLEGAL_FINAL"),
    182: ErrorCodeMeta("ILLEGAL_PREWHERE"),
    183: ErrorCodeMeta("UNEXPECTED_EXPRESSION"),
    184: ErrorCodeMeta("ILLEGAL_AGGREGATION"),
    186: ErrorCodeMeta("UNSUPPORTED_COLLATION_LOCALE"),
    187: ErrorCodeMeta("COLLATION_COMPARISON_FAILED"),
    190: ErrorCodeMeta("SIZES_OF_ARRAYS_DONT_MATCH"),
    191: ErrorCodeMeta("SET_SIZE_LIMIT_EXCEEDED"),
    192: ErrorCodeMeta("UNKNOWN_USER"),
    193: ErrorCodeMeta("WRONG_PASSWORD"),
    194: ErrorCodeMeta("REQUIRED_PASSWORD"),
    195: ErrorCodeMeta("IP_ADDRESS_NOT_ALLOWED"),
    196: ErrorCodeMeta("UNKNOWN_ADDRESS_PATTERN_TYPE"),
    198: ErrorCodeMeta("DNS_ERROR"),
    199: ErrorCodeMeta("UNKNOWN_QUOTA"),
    201: ErrorCodeMeta("QUOTA_EXCEEDED"),
    202: ErrorCodeMeta("TOO_MANY_SIMULTANEOUS_QUERIES"),
    203: ErrorCodeMeta("NO_FREE_CONNECTION"),
    204: ErrorCodeMeta("CANNOT_FSYNC"),
    206: ErrorCodeMeta("ALIAS_REQUIRED"),
    207: ErrorCodeMeta("AMBIGUOUS_IDENTIFIER"),
    208: ErrorCodeMeta("EMPTY_NESTED_TABLE"),
    209: ErrorCodeMeta("SOCKET_TIMEOUT"),
    210: ErrorCodeMeta("NETWORK_ERROR"),
    211: ErrorCodeMeta("EMPTY_QUERY"),
    212: ErrorCodeMeta("UNKNOWN_LOAD_BALANCING"),
    213: ErrorCodeMeta("UNKNOWN_TOTALS_MODE"),
    214: ErrorCodeMeta("CANNOT_STATVFS"),
    215: ErrorCodeMeta("NOT_AN_AGGREGATE"),
    216: ErrorCodeMeta("QUERY_WITH_SAME_ID_IS_ALREADY_RUNNING"),
    217: ErrorCodeMeta("CLIENT_HAS_CONNECTED_TO_WRONG_PORT"),
    218: ErrorCodeMeta("TABLE_IS_DROPPED"),
    219: ErrorCodeMeta("DATABASE_NOT_EMPTY"),
    220: ErrorCodeMeta("DUPLICATE_INTERSERVER_IO_ENDPOINT"),
    221: ErrorCodeMeta("NO_SUCH_INTERSERVER_IO_ENDPOINT"),
    223: ErrorCodeMeta("UNEXPECTED_AST_STRUCTURE"),
    224: ErrorCodeMeta("REPLICA_IS_ALREADY_ACTIVE"),
    225: ErrorCodeMeta("NO_ZOOKEEPER"),
    226: ErrorCodeMeta("NO_FILE_IN_DATA_PART"),
    227: ErrorCodeMeta("UNEXPECTED_FILE_IN_DATA_PART"),
    228: ErrorCodeMeta("BAD_SIZE_OF_FILE_IN_DATA_PART"),
    229: ErrorCodeMeta("QUERY_IS_TOO_LARGE"),
    230: ErrorCodeMeta("NOT_FOUND_EXPECTED_DATA_PART"),
    231: ErrorCodeMeta("TOO_MANY_UNEXPECTED_DATA_PARTS"),
    232: ErrorCodeMeta("NO_SUCH_DATA_PART"),
    233: ErrorCodeMeta("BAD_DATA_PART_NAME"),
    234: ErrorCodeMeta("NO_REPLICA_HAS_PART"),
    235: ErrorCodeMeta("DUPLICATE_DATA_PART"),
    236: ErrorCodeMeta("ABORTED"),
    237: ErrorCodeMeta("NO_REPLICA_NAME_GIVEN"),
    238: ErrorCodeMeta("FORMAT_VERSION_TOO_OLD"),
    239: ErrorCodeMeta("CANNOT_MUNMAP"),
    240: ErrorCodeMeta("CANNOT_MREMAP"),
    241: ErrorCodeMeta("MEMORY_LIMIT_EXCEEDED"),
    242: ErrorCodeMeta("TABLE_IS_READ_ONLY"),
    243: ErrorCodeMeta("NOT_ENOUGH_SPACE"),
    244: ErrorCodeMeta("UNEXPECTED_ZOOKEEPER_ERROR"),
    246: ErrorCodeMeta("CORRUPTED_DATA"),
    248: ErrorCodeMeta("INVALID_PARTITION_VALUE"),
    251: ErrorCodeMeta("NO_SUCH_REPLICA"),
    252: ErrorCodeMeta("TOO_MANY_PARTS"),
    253: ErrorCodeMeta("REPLICA_ALREADY_EXISTS"),
    254: ErrorCodeMeta("NO_ACTIVE_REPLICAS"),
    255: ErrorCodeMeta("TOO_MANY_RETRIES_TO_FETCH_PARTS"),
    256: ErrorCodeMeta("PARTITION_ALREADY_EXISTS"),
    257: ErrorCodeMeta("PARTITION_DOESNT_EXIST"),
    258: ErrorCodeMeta("UNION_ALL_RESULT_STRUCTURES_MISMATCH"),
    260: ErrorCodeMeta("CLIENT_OUTPUT_FORMAT_SPECIFIED"),
    261: ErrorCodeMeta("UNKNOWN_BLOCK_INFO_FIELD"),
    262: ErrorCodeMeta("BAD_COLLATION"),
    263: ErrorCodeMeta("CANNOT_COMPILE_CODE"),
    264: ErrorCodeMeta("INCOMPATIBLE_TYPE_OF_JOIN"),
    265: ErrorCodeMeta("NO_AVAILABLE_REPLICA"),
    266: ErrorCodeMeta("MISMATCH_REPLICAS_DATA_SOURCES"),
    269: ErrorCodeMeta("INFINITE_LOOP"),
    270: ErrorCodeMeta("CANNOT_COMPRESS"),
    271: ErrorCodeMeta("CANNOT_DECOMPRESS"),
    272: ErrorCodeMeta("CANNOT_IO_SUBMIT"),
    273: ErrorCodeMeta("CANNOT_IO_GETEVENTS"),
    274: ErrorCodeMeta("AIO_READ_ERROR"),
    275: ErrorCodeMeta("AIO_WRITE_ERROR"),
    277: ErrorCodeMeta("INDEX_NOT_USED"),
    279: ErrorCodeMeta("ALL_CONNECTION_TRIES_FAILED"),
    280: ErrorCodeMeta("NO_AVAILABLE_DATA"),
    281: ErrorCodeMeta("DICTIONARY_IS_EMPTY"),
    282: ErrorCodeMeta("INCORRECT_INDEX"),
    283: ErrorCodeMeta("UNKNOWN_DISTRIBUTED_PRODUCT_MODE"),
    284: ErrorCodeMeta("WRONG_GLOBAL_SUBQUERY"),
    285: ErrorCodeMeta("TOO_FEW_LIVE_REPLICAS"),
    286: ErrorCodeMeta("UNSATISFIED_QUORUM_FOR_PREVIOUS_WRITE"),
    287: ErrorCodeMeta("UNKNOWN_FORMAT_VERSION"),
    288: ErrorCodeMeta("DISTRIBUTED_IN_JOIN_SUBQUERY_DENIED"),
    289: ErrorCodeMeta("REPLICA_IS_NOT_IN_QUORUM"),
    290: ErrorCodeMeta("LIMIT_EXCEEDED"),
    291: ErrorCodeMeta("DATABASE_ACCESS_DENIED"),
    293: ErrorCodeMeta("MONGODB_CANNOT_AUTHENTICATE"),
    295: ErrorCodeMeta("RECEIVED_EMPTY_DATA"),
    297: ErrorCodeMeta("SHARD_HAS_NO_CONNECTIONS"),
    298: ErrorCodeMeta("CANNOT_PIPE"),
    299: ErrorCodeMeta("CANNOT_FORK"),
    300: ErrorCodeMeta("CANNOT_DLSYM"),
    301: ErrorCodeMeta("CANNOT_CREATE_CHILD_PROCESS"),
    302: ErrorCodeMeta("CHILD_WAS_NOT_EXITED_NORMALLY"),
    303: ErrorCodeMeta("CANNOT_SELECT"),
    304: ErrorCodeMeta("CANNOT_WAITPID"),
    305: ErrorCodeMeta("TABLE_WAS_NOT_DROPPED"),
    306: ErrorCodeMeta("TOO_DEEP_RECURSION"),
    307: ErrorCodeMeta("TOO_MANY_BYTES"),
    308: ErrorCodeMeta("UNEXPECTED_NODE_IN_ZOOKEEPER"),
    309: ErrorCodeMeta("FUNCTION_CANNOT_HAVE_PARAMETERS"),
    318: ErrorCodeMeta("INVALID_CONFIG_PARAMETER"),
    319: ErrorCodeMeta("UNKNOWN_STATUS_OF_INSERT"),
    321: ErrorCodeMeta("VALUE_IS_OUT_OF_RANGE_OF_DATA_TYPE"),
    336: ErrorCodeMeta("UNKNOWN_DATABASE_ENGINE"),
    341: ErrorCodeMeta("UNFINISHED"),
    342: ErrorCodeMeta("METADATA_MISMATCH"),
    344: ErrorCodeMeta("SUPPORT_IS_DISABLED"),
    345: ErrorCodeMeta("TABLE_DIFFERS_TOO_MUCH"),
    346: ErrorCodeMeta("CANNOT_CONVERT_CHARSET"),
    347: ErrorCodeMeta("CANNOT_LOAD_CONFIG"),
    349: ErrorCodeMeta("CANNOT_INSERT_NULL_IN_ORDINARY_COLUMN"),
    352: ErrorCodeMeta("AMBIGUOUS_COLUMN_NAME"),
    353: ErrorCodeMeta("INDEX_OF_POSITIONAL_ARGUMENT_IS_OUT_OF_RANGE"),
    354: ErrorCodeMeta("ZLIB_INFLATE_FAILED"),
    355: ErrorCodeMeta("ZLIB_DEFLATE_FAILED"),
    358: ErrorCodeMeta("INTO_OUTFILE_NOT_ALLOWED"),
    359: ErrorCodeMeta("TABLE_SIZE_EXCEEDS_MAX_DROP_SIZE_LIMIT"),
    360: ErrorCodeMeta("CANNOT_CREATE_CHARSET_CONVERTER"),
    361: ErrorCodeMeta("SEEK_POSITION_OUT_OF_BOUND"),
    362: ErrorCodeMeta("CURRENT_WRITE_BUFFER_IS_EXHAUSTED"),
    363: ErrorCodeMeta("CANNOT_CREATE_IO_BUFFER"),
    364: ErrorCodeMeta("RECEIVED_ERROR_TOO_MANY_REQUESTS"),
    366: ErrorCodeMeta("SIZES_OF_NESTED_COLUMNS_ARE_INCONSISTENT"),
    369: ErrorCodeMeta("ALL_REPLICAS_ARE_STALE"),
    370: ErrorCodeMeta("DATA_TYPE_CANNOT_BE_USED_IN_TABLES"),
    371: ErrorCodeMeta("INCONSISTENT_CLUSTER_DEFINITION"),
    372: ErrorCodeMeta("SESSION_NOT_FOUND"),
    373: ErrorCodeMeta("SESSION_IS_LOCKED"),
    374: ErrorCodeMeta("INVALID_SESSION_TIMEOUT"),
    375: ErrorCodeMeta("CANNOT_DLOPEN"),
    376: ErrorCodeMeta("CANNOT_PARSE_UUID"),
    377: ErrorCodeMeta("ILLEGAL_SYNTAX_FOR_DATA_TYPE"),
    378: ErrorCodeMeta("DATA_TYPE_CANNOT_HAVE_ARGUMENTS"),
    380: ErrorCodeMeta("CANNOT_KILL"),
    381: ErrorCodeMeta("HTTP_LENGTH_REQUIRED"),
    382: ErrorCodeMeta("CANNOT_LOAD_CATBOOST_MODEL"),
    383: ErrorCodeMeta("CANNOT_APPLY_CATBOOST_MODEL"),
    384: ErrorCodeMeta("PART_IS_TEMPORARILY_LOCKED"),
    385: ErrorCodeMeta("MULTIPLE_STREAMS_REQUIRED"),
    386: ErrorCodeMeta("NO_COMMON_TYPE"),
    387: ErrorCodeMeta("DICTIONARY_ALREADY_EXISTS"),
    388: ErrorCodeMeta("CANNOT_ASSIGN_OPTIMIZE"),
    389: ErrorCodeMeta("INSERT_WAS_DEDUPLICATED"),
    390: ErrorCodeMeta("CANNOT_GET_CREATE_TABLE_QUERY"),
    391: ErrorCodeMeta("EXTERNAL_LIBRARY_ERROR"),
    392: ErrorCodeMeta("QUERY_IS_PROHIBITED"),
    393: ErrorCodeMeta("THERE_IS_NO_QUERY"),
    394: ErrorCodeMeta("QUERY_WAS_CANCELLED"),
    395: ErrorCodeMeta("FUNCTION_THROW_IF_VALUE_IS_NON_ZERO"),
    396: ErrorCodeMeta("TOO_MANY_ROWS_OR_BYTES"),
    397: ErrorCodeMeta("QUERY_IS_NOT_SUPPORTED_IN_MATERIALIZED_VIEW"),
    398: ErrorCodeMeta("UNKNOWN_MUTATION_COMMAND"),
    399: ErrorCodeMeta("FORMAT_IS_NOT_SUITABLE_FOR_OUTPUT"),
    400: ErrorCodeMeta("CANNOT_STAT"),
    401: ErrorCodeMeta("FEATURE_IS_NOT_ENABLED_AT_BUILD_TIME"),
    402: ErrorCodeMeta("CANNOT_IOSETUP"),
    403: ErrorCodeMeta("INVALID_JOIN_ON_EXPRESSION"),
    404: ErrorCodeMeta("BAD_ODBC_CONNECTION_STRING"),
    406: ErrorCodeMeta("TOP_AND_LIMIT_TOGETHER"),
    407: ErrorCodeMeta("DECIMAL_OVERFLOW"),
    408: ErrorCodeMeta("BAD_REQUEST_PARAMETER"),
    410: ErrorCodeMeta("EXTERNAL_SERVER_IS_NOT_RESPONDING"),
    411: ErrorCodeMeta("PTHREAD_ERROR"),
    412: ErrorCodeMeta("NETLINK_ERROR"),
    413: ErrorCodeMeta("CANNOT_SET_SIGNAL_HANDLER"),
    415: ErrorCodeMeta("ALL_REPLICAS_LOST"),
    416: ErrorCodeMeta("REPLICA_STATUS_CHANGED"),
    417: ErrorCodeMeta("EXPECTED_ALL_OR_ANY"),
    418: ErrorCodeMeta("UNKNOWN_JOIN"),
    419: ErrorCodeMeta("MULTIPLE_ASSIGNMENTS_TO_COLUMN"),
    420: ErrorCodeMeta("CANNOT_UPDATE_COLUMN"),
    421: ErrorCodeMeta("CANNOT_ADD_DIFFERENT_AGGREGATE_STATES"),
    422: ErrorCodeMeta("UNSUPPORTED_URI_SCHEME"),
    423: ErrorCodeMeta("CANNOT_GETTIMEOFDAY"),
    424: ErrorCodeMeta("CANNOT_LINK"),
    425: ErrorCodeMeta("SYSTEM_ERROR"),
    427: ErrorCodeMeta("CANNOT_COMPILE_REGEXP"),
    429: ErrorCodeMeta("FAILED_TO_GETPWUID"),
    430: ErrorCodeMeta("MISMATCHING_USERS_FOR_PROCESS_AND_DATA"),
    431: ErrorCodeMeta("ILLEGAL_SYNTAX_FOR_CODEC_TYPE"),
    432: ErrorCodeMeta("UNKNOWN_CODEC"),
    433: ErrorCodeMeta("ILLEGAL_CODEC_PARAMETER"),
    434: ErrorCodeMeta("CANNOT_PARSE_PROTOBUF_SCHEMA"),
    435: ErrorCodeMeta("NO_COLUMN_SERIALIZED_TO_REQUIRED_PROTOBUF_FIELD"),
    436: ErrorCodeMeta("PROTOBUF_BAD_CAST"),
    437: ErrorCodeMeta("PROTOBUF_FIELD_NOT_REPEATED"),
    438: ErrorCodeMeta("DATA_TYPE_CANNOT_BE_PROMOTED"),
    439: ErrorCodeMeta("CANNOT_SCHEDULE_TASK"),
    440: ErrorCodeMeta("INVALID_LIMIT_EXPRESSION"),
    441: ErrorCodeMeta("CANNOT_PARSE_DOMAIN_VALUE_FROM_STRING"),
    442: ErrorCodeMeta("BAD_DATABASE_FOR_TEMPORARY_TABLE"),
    443: ErrorCodeMeta("NO_COLUMNS_SERIALIZED_TO_PROTOBUF_FIELDS"),
    444: ErrorCodeMeta("UNKNOWN_PROTOBUF_FORMAT"),
    445: ErrorCodeMeta("CANNOT_MPROTECT"),
    446: ErrorCodeMeta("FUNCTION_NOT_ALLOWED"),
    447: ErrorCodeMeta("HYPERSCAN_CANNOT_SCAN_TEXT"),
    448: ErrorCodeMeta("BROTLI_READ_FAILED"),
    449: ErrorCodeMeta("BROTLI_WRITE_FAILED"),
    450: ErrorCodeMeta("BAD_TTL_EXPRESSION"),
    451: ErrorCodeMeta("BAD_TTL_FILE"),
    452: ErrorCodeMeta("SETTING_CONSTRAINT_VIOLATION"),
    453: ErrorCodeMeta("MYSQL_CLIENT_INSUFFICIENT_CAPABILITIES"),
    454: ErrorCodeMeta("OPENSSL_ERROR"),
    455: ErrorCodeMeta("SUSPICIOUS_TYPE_FOR_LOW_CARDINALITY"),
    456: ErrorCodeMeta("UNKNOWN_QUERY_PARAMETER"),
    457: ErrorCodeMeta("BAD_QUERY_PARAMETER"),
    458: ErrorCodeMeta("CANNOT_UNLINK"),
    459: ErrorCodeMeta("CANNOT_SET_THREAD_PRIORITY"),
    460: ErrorCodeMeta("CANNOT_CREATE_TIMER"),
    461: ErrorCodeMeta("CANNOT_SET_TIMER_PERIOD"),
    463: ErrorCodeMeta("CANNOT_FCNTL"),
    464: ErrorCodeMeta("CANNOT_PARSE_ELF"),
    465: ErrorCodeMeta("CANNOT_PARSE_DWARF"),
    466: ErrorCodeMeta("INSECURE_PATH"),
    467: ErrorCodeMeta("CANNOT_PARSE_BOOL"),
    468: ErrorCodeMeta("CANNOT_PTHREAD_ATTR"),
    469: ErrorCodeMeta("VIOLATED_CONSTRAINT"),
    470: ErrorCodeMeta("QUERY_IS_NOT_SUPPORTED_IN_LIVE_VIEW"),
    471: ErrorCodeMeta("INVALID_SETTING_VALUE"),
    472: ErrorCodeMeta("READONLY_SETTING"),
    473: ErrorCodeMeta("DEADLOCK_AVOIDED"),
    474: ErrorCodeMeta("INVALID_TEMPLATE_FORMAT"),
    475: ErrorCodeMeta("INVALID_WITH_FILL_EXPRESSION"),
    476: ErrorCodeMeta("WITH_TIES_WITHOUT_ORDER_BY"),
    477: ErrorCodeMeta("INVALID_USAGE_OF_INPUT"),
    478: ErrorCodeMeta("UNKNOWN_POLICY"),
    479: ErrorCodeMeta("UNKNOWN_DISK"),
    480: ErrorCodeMeta("UNKNOWN_PROTOCOL"),
    481: ErrorCodeMeta("PATH_ACCESS_DENIED"),
    482: ErrorCodeMeta("DICTIONARY_ACCESS_DENIED"),
    483: ErrorCodeMeta("TOO_MANY_REDIRECTS"),
    484: ErrorCodeMeta("INTERNAL_REDIS_ERROR"),
    487: ErrorCodeMeta("CANNOT_GET_CREATE_DICTIONARY_QUERY"),
    489: ErrorCodeMeta("INCORRECT_DICTIONARY_DEFINITION"),
    490: ErrorCodeMeta("CANNOT_FORMAT_DATETIME"),
    491: ErrorCodeMeta("UNACCEPTABLE_URL"),
    492: ErrorCodeMeta("ACCESS_ENTITY_NOT_FOUND"),
    493: ErrorCodeMeta("ACCESS_ENTITY_ALREADY_EXISTS"),
    495: ErrorCodeMeta("ACCESS_STORAGE_READONLY"),
    496: ErrorCodeMeta("QUOTA_REQUIRES_CLIENT_KEY"),
    497: ErrorCodeMeta("ACCESS_DENIED"),
    498: ErrorCodeMeta("LIMIT_BY_WITH_TIES_IS_NOT_SUPPORTED"),
    499: ErrorCodeMeta("S3_ERROR"),
    500: ErrorCodeMeta("AZURE_BLOB_STORAGE_ERROR"),
    501: ErrorCodeMeta("CANNOT_CREATE_DATABASE"),
    502: ErrorCodeMeta("CANNOT_SIGQUEUE"),
    503: ErrorCodeMeta("AGGREGATE_FUNCTION_THROW"),
    504: ErrorCodeMeta("FILE_ALREADY_EXISTS"),
    507: ErrorCodeMeta("UNABLE_TO_SKIP_UNUSED_SHARDS"),
    508: ErrorCodeMeta("UNKNOWN_ACCESS_TYPE"),
    509: ErrorCodeMeta("INVALID_GRANT"),
    510: ErrorCodeMeta("CACHE_DICTIONARY_UPDATE_FAIL"),
    511: ErrorCodeMeta("UNKNOWN_ROLE"),
    512: ErrorCodeMeta("SET_NON_GRANTED_ROLE"),
    513: ErrorCodeMeta("UNKNOWN_PART_TYPE"),
    514: ErrorCodeMeta("ACCESS_STORAGE_FOR_INSERTION_NOT_FOUND"),
    515: ErrorCodeMeta("INCORRECT_ACCESS_ENTITY_DEFINITION"),
    516: ErrorCodeMeta("AUTHENTICATION_FAILED"),
    517: ErrorCodeMeta("CANNOT_ASSIGN_ALTER"),
    518: ErrorCodeMeta("CANNOT_COMMIT_OFFSET"),
    519: ErrorCodeMeta("NO_REMOTE_SHARD_AVAILABLE"),
    520: ErrorCodeMeta("CANNOT_DETACH_DICTIONARY_AS_TABLE"),
    521: ErrorCodeMeta("ATOMIC_RENAME_FAIL"),
    523: ErrorCodeMeta("UNKNOWN_ROW_POLICY"),
    524: ErrorCodeMeta("ALTER_OF_COLUMN_IS_FORBIDDEN"),
    525: ErrorCodeMeta("INCORRECT_DISK_INDEX"),
    527: ErrorCodeMeta("NO_SUITABLE_FUNCTION_IMPLEMENTATION"),
    528: ErrorCodeMeta("CASSANDRA_INTERNAL_ERROR"),
    529: ErrorCodeMeta("NOT_A_LEADER"),
    530: ErrorCodeMeta("CANNOT_CONNECT_RABBITMQ"),
    531: ErrorCodeMeta("CANNOT_FSTAT"),
    532: ErrorCodeMeta("LDAP_ERROR"),
    535: ErrorCodeMeta("UNKNOWN_RAID_TYPE"),
    536: ErrorCodeMeta("CANNOT_RESTORE_FROM_FIELD_DUMP"),
    537: ErrorCodeMeta("ILLEGAL_MYSQL_VARIABLE"),
    538: ErrorCodeMeta("MYSQL_SYNTAX_ERROR"),
    539: ErrorCodeMeta("CANNOT_BIND_RABBITMQ_EXCHANGE"),
    540: ErrorCodeMeta("CANNOT_DECLARE_RABBITMQ_EXCHANGE"),
    541: ErrorCodeMeta("CANNOT_CREATE_RABBITMQ_QUEUE_BINDING"),
    542: ErrorCodeMeta("CANNOT_REMOVE_RABBITMQ_EXCHANGE"),
    543: ErrorCodeMeta("UNKNOWN_MYSQL_DATATYPES_SUPPORT_LEVEL"),
    544: ErrorCodeMeta("ROW_AND_ROWS_TOGETHER"),
    545: ErrorCodeMeta("FIRST_AND_NEXT_TOGETHER"),
    546: ErrorCodeMeta("NO_ROW_DELIMITER"),
    547: ErrorCodeMeta("INVALID_RAID_TYPE"),
    548: ErrorCodeMeta("UNKNOWN_VOLUME"),
    549: ErrorCodeMeta("DATA_TYPE_CANNOT_BE_USED_IN_KEY"),
    552: ErrorCodeMeta("UNRECOGNIZED_ARGUMENTS"),
    553: ErrorCodeMeta("LZMA_STREAM_ENCODER_FAILED"),
    554: ErrorCodeMeta("LZMA_STREAM_DECODER_FAILED"),
    555: ErrorCodeMeta("ROCKSDB_ERROR"),
    556: ErrorCodeMeta("SYNC_MYSQL_USER_ACCESS_ERROR"),
    557: ErrorCodeMeta("UNKNOWN_UNION"),
    558: ErrorCodeMeta("EXPECTED_ALL_OR_DISTINCT"),
    559: ErrorCodeMeta("INVALID_GRPC_QUERY_INFO"),
    560: ErrorCodeMeta("ZSTD_ENCODER_FAILED"),
    561: ErrorCodeMeta("ZSTD_DECODER_FAILED"),
    562: ErrorCodeMeta("TLD_LIST_NOT_FOUND"),
    563: ErrorCodeMeta("CANNOT_READ_MAP_FROM_TEXT"),
    564: ErrorCodeMeta("INTERSERVER_SCHEME_DOESNT_MATCH"),
    565: ErrorCodeMeta("TOO_MANY_PARTITIONS"),
    566: ErrorCodeMeta("CANNOT_RMDIR"),
    567: ErrorCodeMeta("DUPLICATED_PART_UUIDS"),
    568: ErrorCodeMeta("RAFT_ERROR"),
    569: ErrorCodeMeta("MULTIPLE_COLUMNS_SERIALIZED_TO_SAME_PROTOBUF_FIELD"),
    570: ErrorCodeMeta("DATA_TYPE_INCOMPATIBLE_WITH_PROTOBUF_FIELD"),
    571: ErrorCodeMeta("DATABASE_REPLICATION_FAILED"),
    572: ErrorCodeMeta("TOO_MANY_QUERY_PLAN_OPTIMIZATIONS"),
    573: ErrorCodeMeta("EPOLL_ERROR"),
    574: ErrorCodeMeta("DISTRIBUTED_TOO_MANY_PENDING_BYTES"),
    575: ErrorCodeMeta("UNKNOWN_SNAPSHOT"),
    576: ErrorCodeMeta("KERBEROS_ERROR"),
    577: ErrorCodeMeta("INVALID_SHARD_ID"),
    578: ErrorCodeMeta("INVALID_FORMAT_INSERT_QUERY_WITH_DATA"),
    579: ErrorCodeMeta("INCORRECT_PART_TYPE"),
    580: ErrorCodeMeta("CANNOT_SET_ROUNDING_MODE"),
    581: ErrorCodeMeta("TOO_LARGE_DISTRIBUTED_DEPTH"),
    582: ErrorCodeMeta("NO_SUCH_PROJECTION_IN_TABLE"),
    583: ErrorCodeMeta("ILLEGAL_PROJECTION"),
    584: ErrorCodeMeta("PROJECTION_NOT_USED"),
    585: ErrorCodeMeta("CANNOT_PARSE_YAML"),
    586: ErrorCodeMeta("CANNOT_CREATE_FILE"),
    587: ErrorCodeMeta("CONCURRENT_ACCESS_NOT_SUPPORTED"),
    588: ErrorCodeMeta("DISTRIBUTED_BROKEN_BATCH_INFO"),
    589: ErrorCodeMeta("DISTRIBUTED_BROKEN_BATCH_FILES"),
    590: ErrorCodeMeta("CANNOT_SYSCONF"),
    591: ErrorCodeMeta("SQLITE_ENGINE_ERROR"),
    592: ErrorCodeMeta("DATA_ENCRYPTION_ERROR"),
    593: ErrorCodeMeta("ZERO_COPY_REPLICATION_ERROR"),
    594: ErrorCodeMeta("BZIP2_STREAM_DECODER_FAILED"),
    595: ErrorCodeMeta("BZIP2_STREAM_ENCODER_FAILED"),
    596: ErrorCodeMeta("INTERSECT_OR_EXCEPT_RESULT_STRUCTURES_MISMATCH"),
    597: ErrorCodeMeta("NO_SUCH_ERROR_CODE"),
    598: ErrorCodeMeta("BACKUP_ALREADY_EXISTS"),
    599: ErrorCodeMeta("BACKUP_NOT_FOUND"),
    600: ErrorCodeMeta("BACKUP_VERSION_NOT_SUPPORTED"),
    601: ErrorCodeMeta("BACKUP_DAMAGED"),
    602: ErrorCodeMeta("NO_BASE_BACKUP"),
    603: ErrorCodeMeta("WRONG_BASE_BACKUP"),
    604: ErrorCodeMeta("BACKUP_ENTRY_ALREADY_EXISTS"),
    605: ErrorCodeMeta("BACKUP_ENTRY_NOT_FOUND"),
    606: ErrorCodeMeta("BACKUP_IS_EMPTY"),
    607: ErrorCodeMeta("CANNOT_RESTORE_DATABASE"),
    608: ErrorCodeMeta("CANNOT_RESTORE_TABLE"),
    609: ErrorCodeMeta("FUNCTION_ALREADY_EXISTS"),
    610: ErrorCodeMeta("CANNOT_DROP_FUNCTION"),
    611: ErrorCodeMeta("CANNOT_CREATE_RECURSIVE_FUNCTION"),
    614: ErrorCodeMeta("POSTGRESQL_CONNECTION_FAILURE"),
    615: ErrorCodeMeta("CANNOT_ADVISE"),
    616: ErrorCodeMeta("UNKNOWN_READ_METHOD"),
    617: ErrorCodeMeta("LZ4_ENCODER_FAILED"),
    618: ErrorCodeMeta("LZ4_DECODER_FAILED"),
    619: ErrorCodeMeta("POSTGRESQL_REPLICATION_INTERNAL_ERROR"),
    620: ErrorCodeMeta("QUERY_NOT_ALLOWED"),
    621: ErrorCodeMeta("CANNOT_NORMALIZE_STRING"),
    622: ErrorCodeMeta("CANNOT_PARSE_CAPN_PROTO_SCHEMA"),
    623: ErrorCodeMeta("CAPN_PROTO_BAD_CAST"),
    624: ErrorCodeMeta("BAD_FILE_TYPE"),
    625: ErrorCodeMeta("IO_SETUP_ERROR"),
    626: ErrorCodeMeta("CANNOT_SKIP_UNKNOWN_FIELD"),
    627: ErrorCodeMeta("BACKUP_ENGINE_NOT_FOUND"),
    628: ErrorCodeMeta("OFFSET_FETCH_WITHOUT_ORDER_BY"),
    629: ErrorCodeMeta("HTTP_RANGE_NOT_SATISFIABLE"),
    630: ErrorCodeMeta("HAVE_DEPENDENT_OBJECTS"),
    631: ErrorCodeMeta("UNKNOWN_FILE_SIZE"),
    632: ErrorCodeMeta("UNEXPECTED_DATA_AFTER_PARSED_VALUE"),
    633: ErrorCodeMeta("QUERY_IS_NOT_SUPPORTED_IN_WINDOW_VIEW"),
    634: ErrorCodeMeta("MONGODB_ERROR"),
    635: ErrorCodeMeta("CANNOT_POLL"),
    636: ErrorCodeMeta("CANNOT_EXTRACT_TABLE_STRUCTURE"),
    637: ErrorCodeMeta("INVALID_TABLE_OVERRIDE"),
    638: ErrorCodeMeta("SNAPPY_UNCOMPRESS_FAILED"),
    639: ErrorCodeMeta("SNAPPY_COMPRESS_FAILED"),
    640: ErrorCodeMeta("NO_HIVEMETASTORE"),
    641: ErrorCodeMeta("CANNOT_APPEND_TO_FILE"),
    642: ErrorCodeMeta("CANNOT_PACK_ARCHIVE"),
    643: ErrorCodeMeta("CANNOT_UNPACK_ARCHIVE"),
    645: ErrorCodeMeta("NUMBER_OF_DIMENSIONS_MISMATCHED"),
    647: ErrorCodeMeta("CANNOT_BACKUP_TABLE"),
    648: ErrorCodeMeta("WRONG_DDL_RENAMING_SETTINGS"),
    649: ErrorCodeMeta("INVALID_TRANSACTION"),
    650: ErrorCodeMeta("SERIALIZATION_ERROR"),
    651: ErrorCodeMeta("CAPN_PROTO_BAD_TYPE"),
    652: ErrorCodeMeta("ONLY_NULLS_WHILE_READING_SCHEMA"),
    653: ErrorCodeMeta("CANNOT_PARSE_BACKUP_SETTINGS"),
    654: ErrorCodeMeta("WRONG_BACKUP_SETTINGS"),
    655: ErrorCodeMeta("FAILED_TO_SYNC_BACKUP_OR_RESTORE"),
    659: ErrorCodeMeta("UNKNOWN_STATUS_OF_TRANSACTION"),
    660: ErrorCodeMeta("HDFS_ERROR"),
    661: ErrorCodeMeta("CANNOT_SEND_SIGNAL"),
    662: ErrorCodeMeta("FS_METADATA_ERROR"),
    663: ErrorCodeMeta("INCONSISTENT_METADATA_FOR_BACKUP"),
    664: ErrorCodeMeta("ACCESS_STORAGE_DOESNT_ALLOW_BACKUP"),
    665: ErrorCodeMeta("CANNOT_CONNECT_NATS"),
    667: ErrorCodeMeta("NOT_INITIALIZED"),
    668: ErrorCodeMeta("INVALID_STATE"),
    669: ErrorCodeMeta("NAMED_COLLECTION_DOESNT_EXIST"),
    670: ErrorCodeMeta("NAMED_COLLECTION_ALREADY_EXISTS"),
    671: ErrorCodeMeta("NAMED_COLLECTION_IS_IMMUTABLE"),
    672: ErrorCodeMeta("INVALID_SCHEDULER_NODE"),
    673: ErrorCodeMeta("RESOURCE_ACCESS_DENIED"),
    674: ErrorCodeMeta("RESOURCE_NOT_FOUND"),
    675: ErrorCodeMeta("CANNOT_PARSE_IPV4"),
    676: ErrorCodeMeta("CANNOT_PARSE_IPV6"),
    677: ErrorCodeMeta("THREAD_WAS_CANCELED"),
    678: ErrorCodeMeta("IO_URING_INIT_FAILED"),
    679: ErrorCodeMeta("IO_URING_SUBMIT_ERROR"),
    690: ErrorCodeMeta("MIXED_ACCESS_PARAMETER_TYPES"),
    691: ErrorCodeMeta("UNKNOWN_ELEMENT_OF_ENUM"),
    692: ErrorCodeMeta("TOO_MANY_MUTATIONS"),
    693: ErrorCodeMeta("AWS_ERROR"),
    694: ErrorCodeMeta("ASYNC_LOAD_CYCLE"),
    695: ErrorCodeMeta("ASYNC_LOAD_FAILED"),
    696: ErrorCodeMeta("ASYNC_LOAD_CANCELED"),
    697: ErrorCodeMeta("CANNOT_RESTORE_TO_NONENCRYPTED_DISK"),
    698: ErrorCodeMeta("INVALID_REDIS_STORAGE_TYPE"),
    699: ErrorCodeMeta("INVALID_REDIS_TABLE_STRUCTURE"),
    700: ErrorCodeMeta("USER_SESSION_LIMIT_EXCEEDED"),
    701: ErrorCodeMeta("CLUSTER_DOESNT_EXIST"),
    702: ErrorCodeMeta("CLIENT_INFO_DOES_NOT_MATCH"),
    703: ErrorCodeMeta("INVALID_IDENTIFIER"),
    704: ErrorCodeMeta("QUERY_CACHE_USED_WITH_NONDETERMINISTIC_FUNCTIONS"),
    705: ErrorCodeMeta("TABLE_NOT_EMPTY"),
    706: ErrorCodeMeta("LIBSSH_ERROR"),
    707: ErrorCodeMeta("GCP_ERROR"),
    708: ErrorCodeMeta("ILLEGAL_STATISTIC"),
    709: ErrorCodeMeta("CANNOT_GET_REPLICATED_DATABASE_SNAPSHOT"),
    999: ErrorCodeMeta("KEEPER_EXCEPTION"),
    1000: ErrorCodeMeta("POCO_EXCEPTION"),
    1001: ErrorCodeMeta("STD_EXCEPTION"),
    1002: ErrorCodeMeta("UNKNOWN_EXCEPTION"),
}
