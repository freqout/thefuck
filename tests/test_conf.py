import pytest
import six
from mock import Mock
from thefuck import conf
from tests.utils import Rule


@pytest.mark.parametrize('enabled, rules, result', [
    (True, conf.DEFAULT_RULES, True),
    (False, conf.DEFAULT_RULES, False),
    (False, conf.DEFAULT_RULES + ['test'], True)])
def test_default(enabled, rules, result):
    assert (Rule('test', enabled_by_default=enabled) in rules) == result


@pytest.fixture
def load_source(mocker):
    return mocker.patch('thefuck.conf.load_source')


@pytest.fixture
def environ(monkeypatch):
    data = {}
    monkeypatch.setattr('thefuck.conf.os.environ', data)
    return data


@pytest.mark.usefixture('environ')
def test_settings_defaults(load_source):
    load_source.return_value = object()
    for key, val in conf.DEFAULT_SETTINGS.items():
        assert getattr(conf.get_settings(Mock()), key) == val


@pytest.mark.usefixture('environ')
class TestSettingsFromFile(object):
    def test_from_file(self, load_source):
        load_source.return_value = Mock(rules=['test'],
                                        wait_command=10,
                                        require_confirmation=True,
                                        no_colors=True,
                                        priority={'vim': 100})
        settings = conf.get_settings(Mock())
        assert settings.rules == ['test']
        assert settings.wait_command == 10
        assert settings.require_confirmation is True
        assert settings.no_colors is True
        assert settings.priority == {'vim': 100}

    def test_from_file_with_DEFAULT(self, load_source):
        load_source.return_value = Mock(rules=conf.DEFAULT_RULES + ['test'],
                                        wait_command=10,
                                        require_confirmation=True,
                                        no_colors=True)
        settings = conf.get_settings(Mock())
        assert settings.rules == conf.DEFAULT_RULES + ['test']


@pytest.mark.usefixture('load_source')
class TestSettingsFromEnv(object):
    def test_from_env(self, environ):
        environ.update({'THEFUCK_RULES': 'bash:lisp',
                        'THEFUCK_WAIT_COMMAND': '55',
                        'THEFUCK_REQUIRE_CONFIRMATION': 'true',
                        'THEFUCK_NO_COLORS': 'false',
                        'THEFUCK_PRIORITY': 'bash=10:lisp=wrong:vim=15'})
        settings = conf.get_settings(Mock())
        assert settings.rules == ['bash', 'lisp']
        assert settings.wait_command == 55
        assert settings.require_confirmation is True
        assert settings.no_colors is False
        assert settings.priority == {'bash': 10, 'vim': 15}

    def test_from_env_with_DEFAULT(self, environ):
        environ.update({'THEFUCK_RULES': 'DEFAULT_RULES:bash:lisp'})
        settings = conf.get_settings(Mock())
        assert settings.rules == conf.DEFAULT_RULES + ['bash', 'lisp']


class TestInitializeSettingsFile(object):
    def test_ignore_if_exists(self):
        settings_path_mock = Mock(is_file=Mock(return_value=True), open=Mock())
        user_dir_mock = Mock(joinpath=Mock(return_value=settings_path_mock))
        conf.initialize_settings_file(user_dir_mock)
        assert settings_path_mock.is_file.call_count == 1
        assert not settings_path_mock.open.called

    def test_create_if_doesnt_exists(self):
        settings_file = six.StringIO()
        settings_path_mock = Mock(
            is_file=Mock(return_value=False),
            open=Mock(return_value=Mock(
                __exit__=lambda *args: None, __enter__=lambda *args: settings_file)))
        user_dir_mock = Mock(joinpath=Mock(return_value=settings_path_mock))
        conf.initialize_settings_file(user_dir_mock)
        settings_file_contents = settings_file.getvalue()
        assert settings_path_mock.is_file.call_count == 1
        assert settings_path_mock.open.call_count == 1
        assert conf.SETTINGS_HEADER in settings_file_contents
        for setting in conf.DEFAULT_SETTINGS.items():
            assert '# {} = {}\n'.format(*setting) in settings_file_contents
        settings_file.close()
