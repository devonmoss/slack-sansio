import time
import json
import copy
import pytest
import requests
import asynctest
import functools

from unittest.mock import Mock

from slack.io.abc import SlackAPI
from slack.io.requests import SlackAPI as SlackAPIRequest
from slack.events import Event, EventRouter, MessageRouter
from slack.actions import Action, Router as ActionRouter
from slack.commands import Command, Router as CommandRouter

from . import data

TOKEN = 'abcdefg'


class FakeIO(SlackAPI):
    async def _request(self, method, url, headers, body):
        pass

    async def sleep(self, seconds):
        time.sleep(seconds)

    async def _rtm(self, url):
        pass


@pytest.fixture(params=(data.events.rtm_events.keys(),))
def rtm_iterator(request):
    async def events(url):
        for key in request.param:
            yield data.events.rtm_events[key]
    return events


@pytest.fixture(params=(data.events.rtm_events.keys(),))
def rtm_iterator_non_async(request):
    def events(url):
        for key in request.param:
            yield data.events.rtm_events[key]
    return events


@pytest.fixture(params=(FakeIO, ))
def io_client(request):

    if request.param is SlackAPIRequest:
        return functools.partial(request.param, session=requests.session())
    return request.param


@pytest.fixture(params=({'retry_when_rate_limit': True, 'token': TOKEN},
                        {'retry_when_rate_limit': False, 'token': TOKEN}))
def client(request, io_client):
    default_request = {'status': 200, 'body': {'ok': True},
                       'headers': {'content-type': 'application/json; charset=utf-8'}}

    if '_request' not in request.param:
        request.param['_request'] = default_request
    elif isinstance(request.param['_request'], dict):
        request.param['_request'] = _default_response(request.param['_request'])
    elif isinstance(request.param['_request'], list):
        for index, item in enumerate(request.param['_request']):
            request.param['_request'][index] = _default_response(item)

    if 'token' not in request.param:
        request.param['token'] = TOKEN

    slackclient = io_client(**{k: v for k, v in request.param.items() if not k.startswith('_')})

    if isinstance(request.param['_request'], dict):
        return_value = (
            request.param['_request']['status'],
            json.dumps(request.param['_request']['body']).encode(),
            request.param['_request']['headers']
        )
        if isinstance(slackclient, SlackAPIRequest):
            slackclient._request = Mock(return_value=return_value)
        else:
            slackclient._request = asynctest.CoroutineMock(return_value=return_value)
    else:
        responses = [
            (response['status'], json.dumps(response['body']).encode(), response['headers'])
            for response in request.param['_request']
        ]
        if isinstance(slackclient, SlackAPIRequest):
            slackclient._request = Mock(side_effect=responses)
        else:
            slackclient._request = asynctest.CoroutineMock(side_effect=responses)

    return slackclient


def _default_response(response):
    default_response = {'status': 200, 'body': {'ok': True},
                        'headers': {'content-type': 'application/json; charset=utf-8'}}
    response = {**default_response, **response}
    if 'content-type' not in response['headers']:
        response['headers']['content-type'] = default_response['headers']['content-type']
    if isinstance(response['body'], str):
        response['body'] = copy.deepcopy(data.methods.payloads[response['body']])
    return response


@pytest.fixture(params={**data.events.events, **data.events.message})
def raw_event(request):
    if isinstance(request.param, str):
        if request.param in data.events.events:
            return copy.deepcopy(data.events.events[request.param])
        elif request.param in data.events.message:
            return copy.deepcopy(data.events.message[request.param])
        else:
            raise ValueError(f'Event "{request.param}" not found')
    else:
        return copy.deepcopy(request.param)


@pytest.fixture(params={**data.events.events, **data.events.message})
def event(request):
    return Event.from_http(raw_event(request))


@pytest.fixture(params={**data.events.message})
def message(request):
    return Event.from_http(raw_event(request))


@pytest.fixture()
def token():
    return copy.copy(TOKEN)


@pytest.fixture()
def itercursor():
    return 'wxyz'


@pytest.fixture()
def event_router():
    return EventRouter()


@pytest.fixture()
def message_router():
    return MessageRouter()


@pytest.fixture(params={**data.actions.actions})
def action(request):
    return Action.from_http(raw_action(request))


@pytest.fixture(params={**data.actions.actions})
def raw_action(request):
    if isinstance(request.param, str):
        if request.param in data.actions.actions:
            return copy.deepcopy(data.actions.actions[request.param])
        else:
            raise ValueError(f'Raw action "{request.param}" not found')
    else:
        return copy.deepcopy(request.param)


@pytest.fixture()
def action_router():
    return ActionRouter()


@pytest.fixture(params={**data.commands.commands})
def raw_command(request):
    if isinstance(request.param, str):
        if request.param in data.commands.commands:
            return copy.deepcopy(data.commands.commands[request.param])
        else:
            raise ValueError(f'Command "{request.param}" not found')
    else:
        return copy.deepcopy(request.param)


@pytest.fixture(params={**data.commands.commands})
def command(request):
    return Command(raw_command(request))


@pytest.fixture()
def command_router():
    return CommandRouter()