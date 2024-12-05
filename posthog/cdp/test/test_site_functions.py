import subprocess
import tempfile
from inline_snapshot import snapshot
import pytest
from django.test import TestCase
from posthog.cdp.site_functions import get_transpiled_function
from posthog.models.action.action import Action
from posthog.models.hog_functions.hog_function import HogFunction
from posthog.models.organization import Organization
from posthog.models.project import Project
from posthog.models.plugin import TranspilerError
from posthog.models.group_type_mapping import GroupTypeMapping
from posthog.models.user import User


class TestSiteFunctions(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Test Organization")
        self.user = User.objects.create_user(email="testuser@example.com", first_name="Test", password="password")
        self.organization.members.add(self.user)
        self.project, self.team = Project.objects.create_with_team(
            initiating_user=self.user,
            organization=self.organization,
            name="Test project",
        )

        self.hog_function = HogFunction(
            id="123",
            team=self.team,
            name="Test Hog Function",
            hog='export function onLoad() { console.log("Hello, World!"); }',
            filters={},
            inputs={},
        )

    def compile_and_run(self):
        result = get_transpiled_function(self.hog_function)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(result.encode("utf-8"))
            f.flush()
            # NOTE: Nodejs isn't the right environment as it is really for the browser but we are only checking the output is valid, not that it actually runs
            # More of a sanity check that our templating isn't broken
            output = subprocess.check_output(["node", f.name])
            assert output == b""

        return result

    def test_get_transpiled_function_basic(self):
        result = self.compile_and_run()
        assert isinstance(result, str)
        assert 'console.log("Hello, World!")' in result

        # NOTE: We do one inlne snapshot here so we can have an easy glance at what it generally looks like - all other tests we should just check specific parts
        assert result == snapshot(
            """\
(function() {


function buildInputs(globals, initial) {
let inputs = {
};
let __getGlobal = (key) => key === 'inputs' ? inputs : globals[key];
return inputs;}
const source = (function () {let exports={};"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.onLoad = onLoad;
function onLoad() {
  console.log("Hello, World!");
};return exports;})();
    let processEvent = undefined;
    if ('onEvent' in source) {
        processEvent = function processEvent(globals) {
            if (!('onEvent' in source)) { return; };
            const inputs = buildInputs(globals);
            const filterGlobals = { ...globals.groups, ...globals.event, person: globals.person, inputs, pdi: { distinct_id: globals.event.distinct_id, person: globals.person } };
            let __getGlobal = (key) => filterGlobals[key];
            const filterMatches = true;
            if (filterMatches) { source.onEvent({ ...globals, inputs, posthog }); }
        }
    }

    function init(config) {
        const posthog = config.posthog;
        const callback = config.callback;
        if ('onLoad' in source) {
            const r = source.onLoad({ inputs: buildInputs({}, true), posthog: posthog });
            if (r && typeof r.then === 'function' && typeof r.finally === 'function') { r.catch(() => callback(false)).then(() => callback(true)) } else { callback(true) }
        } else {
            callback(true);
        }

        return {
            processEvent: processEvent
        }
    }

    return { init: init };
    
})\
"""
        )

    def test_get_transpiled_function_with_static_input(self):
        self.hog_function.hog = "export function onLoad() { console.log(inputs.message); }"
        self.hog_function.inputs = {"message": {"value": "Hello, Inputs!"}}

        result = self.compile_and_run()

        assert "console.log(inputs.message);" in result
        assert "inputs = {" in result
        assert '"message": "Hello, Inputs!"' in result

    def test_get_transpiled_function_with_template_input(self):
        self.hog_function.hog = "export function onLoad() { console.log(inputs.greeting); }"
        self.hog_function.inputs = {"greeting": {"value": "Hello, {person.properties.name}!"}}
        result = self.compile_and_run()

        assert "console.log(inputs.greeting);" in result
        assert "function getInputsKey" in result
        assert 'inputs["greeting"] = getInputsKey("greeting");' in result
        assert 'case "greeting": return ' in result
        assert '__getGlobal("person")' in result

    def test_get_transpiled_function_with_filters(self):
        self.hog_function.hog = "export function onEvent(event) { console.log(event.event); }"
        self.hog_function.filters = {"events": [{"id": "$pageview", "name": "$pageview", "type": "events", "order": 0}]}

        result = self.compile_and_run()

        assert "console.log(event.event);" in result
        assert "const filterMatches = " in result
        assert '__getGlobal("event") == "$pageview"' in result
        assert "if (filterMatches) { source.onEvent({" in result

    def test_get_transpiled_function_with_invalid_template_input(self):
        self.hog_function.hog = "export function onLoad() { console.log(inputs.greeting); }"
        self.hog_function.inputs = {"greeting": {"value": "Hello, {person.properties.nonexistent_property}!"}}

        result = self.compile_and_run()

        assert "console.log(inputs.greeting);" in result

    def test_get_transpiled_function_with_syntax_error_in_source(self):
        self.hog_function.hog = 'export function onLoad() { console.log("Missing closing brace");'

        with pytest.raises(TranspilerError):
            get_transpiled_function(self.hog_function)

    def test_get_transpiled_function_with_complex_inputs(self):
        self.hog_function.hog = "export function onLoad() { console.log(inputs.complexInput); }"
        self.hog_function.inputs = {
            "complexInput": {
                "value": {
                    "nested": "{event.properties.url}",
                    "list": ["{person.properties.name}", "{groups.group_name}"],
                }
            }
        }

        result = self.compile_and_run()

        assert "console.log(inputs.complexInput);" in result
        assert "function getInputsKey" in result
        assert 'inputs["complexInput"] = getInputsKey("complexInput");' in result

    def test_get_transpiled_function_with_empty_inputs(self):
        self.hog_function.hog = 'export function onLoad() { console.log("No inputs"); }'
        self.hog_function.inputs = {}

        result = self.compile_and_run()

        assert 'console.log("No inputs");' in result
        assert "let inputs = {\n};" in result

    def test_get_transpiled_function_with_non_template_string(self):
        self.hog_function.hog = "export function onLoad() { console.log(inputs.staticMessage); }"
        self.hog_function.inputs = {"staticMessage": {"value": "This is a static message."}}

        result = self.compile_and_run()

        assert "console.log(inputs.staticMessage);" in result
        assert '"staticMessage": "This is a static message."' in result
        assert "function getInputsKey" not in result

    def test_get_transpiled_function_with_list_inputs(self):
        self.hog_function.hog = "export function onLoad() { console.log(inputs.messages); }"
        self.hog_function.inputs = {"messages": {"value": ["Hello", "World", "{person.properties.name}"]}}

        result = self.compile_and_run()

        assert "console.log(inputs.messages);" in result
        assert "function getInputsKey" in result
        assert 'inputs["messages"] = getInputsKey("messages");' in result

    def test_get_transpiled_function_with_event_filter(self):
        self.hog_function.hog = "export function onEvent(event) { console.log(event.properties.url); }"
        self.hog_function.filters = {
            "events": [{"id": "$pageview", "name": "$pageview", "type": "events"}],
            "filter_test_accounts": True,
        }

        self.team.test_account_filters = [
            {"key": "email", "value": "@test.com", "operator": "icontains", "type": "person"}
        ]
        self.team.save()

        result = self.compile_and_run()

        assert "console.log(event.properties.url);" in result
        assert "const filterMatches = " in result
        assert '__getGlobal("event") == "$pageview"' in result
        assert (
            '(ilike(__getProperty(__getProperty(__getGlobal("person"), "properties", true), "email", true), "%@test.com%")'
            in result
        )

    def test_get_transpiled_function_with_groups(self):
        self.hog_function.hog = "export function onLoad() { console.log(inputs.groupInfo); }"
        self.hog_function.inputs = {"groupInfo": {"value": "{groups['company']}"}}

        GroupTypeMapping.objects.create(team=self.team, group_type="company", group_type_index=0, project=self.project)

        result = self.compile_and_run()

        assert "console.log(inputs.groupInfo);" in result
        assert 'inputs["groupInfo"] = getInputsKey("groupInfo");' in result
        assert '__getProperty(__getGlobal("groups"), "company", false)' in result

    def test_get_transpiled_function_with_missing_group(self):
        self.hog_function.hog = "export function onLoad() { console.log(inputs.groupInfo); }"
        self.hog_function.inputs = {"groupInfo": {"value": "{groups['nonexistent']}"}}

        result = self.compile_and_run()

        assert "console.log(inputs.groupInfo);" in result
        assert 'inputs["groupInfo"] = getInputsKey("groupInfo");' in result
        assert '__getProperty(__getGlobal("groups"), "nonexistent"' in result

    def test_get_transpiled_function_with_complex_filters(self):
        action = Action.objects.create(team=self.team, name="Test Action")
        action.steps = [{"event": "$pageview", "url": "https://example.com"}]  # type: ignore
        action.save()

        self.hog_function.hog = "export function onEvent(event) { console.log(event.event); }"
        self.hog_function.filters = {
            "events": [{"id": "$pageview", "name": "$pageview", "type": "events"}],
            "actions": [{"id": str(action.pk), "name": "Test Action", "type": "actions"}],
            "filter_test_accounts": True,
        }

        result = self.compile_and_run()

        assert "console.log(event.event);" in result
        assert "const filterMatches = " in result
        assert '__getGlobal("event") == "$pageview"' in result
        assert "https://example.com" in result
