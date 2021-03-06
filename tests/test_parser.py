from builtins import str

import pytest  # flake8: noqa
import yaml

from shrun import parser


def parse_command(command):
    return list(parser.generate_commands([command]))


class TestGenerateCommands:
    def test_features(self):
        """ Features and command are separated """
        assert list(parser.generate_commands(yaml.load(
            '- my_command: {name: my_name}'))) == [('my_command', {'name': 'my_name'})]

    def test_invalid_feature_key(self):
        """ Check that only valid keywords are used """
        with pytest.raises(AssertionError):
            parse_command({'sleep 1000': {'backgroundish': True}})

    def test_badly_formatted_entry(self):
        """ Test that a command object has only one-key """
        with pytest.raises(AssertionError) as exc_info:
            list(parser.generate_commands(yaml.load("""
                - key1: 1
                  key2: 2
                """)))
        assert "Command has multiple top-level keys: ['key1', 'key2']" in str(exc_info.value)

    def test_removes_trailing_newline_from_complex_keys(self):
        """ Check that only valid keywords are used """
        commands = list(parser.generate_commands(yaml.load("""
            - ? >
                  Line 1
                  Line 2
              : retries: 1
            """)))
        assert commands == [('Line 1 Line 2', {'retries': 1})]


class TestSeries:
    def test_simple_series(self):
        """ A separate command is generated for each series """
        assert parse_command('test{{A,B}}') == [('testA', {}), ('testB', {})]

    def test_labeled_series(self):
        """ Series are expanded when their name matches an existing series. """
        assert parse_command('test{{my_series:A,B}}{{my_series}}') == [('testAA', {}), ('testBB', {})]

    def test_multiple_series(self):
        """ Multiple series generate the cross-product """
        assert parse_command('test{{A,B}}{{1,2}}') == [
            ('testA1', {}), ('testA2', {}), ('testB1', {}), ('testB2', {})]

    def test_multiple_identical_series(self):
        """ Identical series are expanded together """
        assert parse_command('test{{A,B}}{{A,B}}') == [
            ('testAA', {}), ('testBB', {})]

    def test_series_in_features(self):
        """ Series are expanded in features """
        assert parse_command({'test{{A,B}}': {'depends_on': 'name{{A,B}}'}}) == [
            ('testA', {'depends_on': 'nameA'}), ('testB', {'depends_on': 'nameB'})]

    def test_labeled_series(self):
        """ Series are expanded when their name matches an existing series. """
        assert parse_command('test{{my_series:A,B}}{{my_series}}') == [('testAA', {}), ('testBB', {})]

    def test_labeled_series_map_1_to_1(self):
        """ Series are mapped 1-1 to new values if the series label matches. """
        assert parse_command('test{{my_series:A,B}}{{my_series:1,2}}') == [('testA1', {}), ('testB2', {})]

    def test_labeled_series_must_map_1_to_1(self):
        """ Series are mapped 1-1 to new values if the group label matches. """
        with pytest.raises(AssertionError) as exc_info:
            parse_command('test{{my_series:A,B}}{{my_series:1,2,3}}')
        assert "Mapping for series 'my_series' must be 1-1" in str(exc_info.value)


class TestSequences:
    def test_simple_foreach_sequence(self):
        """ Sequences are repeated for each item in the 'foreach' series. """
        assert list(parser.generate_commands(yaml.load("""
            - foreach: my_series:A,B
            - echo test{{my_series}}_{{x,y}}
            - echo test2{{my_series}}
        """))) == [('echo testA_x', {}), ('echo testA_y', {}), ('echo test2A', {}),
                   ('echo testB_x', {}), ('echo testB_y', {}), ('echo test2B', {})]

    def test_labeled_foreach_series(self):
        """ Sequences are repeated for each item in the 'foreach' series. """
        assert list(parser.generate_commands(yaml.load("""
            - foreach: {my_series: [A,B]}
            - echo test{{my_series}}
        """))) == [('echo testA', {}), ('echo testB', {})]

    def test_unlabeled_foreach_series(self):
        """ Sequences are repeated for each item in the 'foreach' series. """
        assert list(parser.generate_commands(yaml.load("""
            - foreach: [A,B]
            - echo test{{A,B}}
        """))) == [('echo testA', {}), ('echo testB', {})]

    def test_nested_foreach_sequences(self):
        """ Sequences are expanded based using the 'foreach' feature. """
        assert list(parser.generate_commands(yaml.load("""
            - foreach: my_series:A,B
            - - foreach: 1,2
              - echo test{{my_series}}_{{1,2}}
        """))) == [('echo testA_1', {}), ('echo testA_2', {}),
                   ('echo testB_1', {}), ('echo testB_2', {})]

    def test_nested_foreach_sequences_with_same_name_error(self):
        """ A series label cannot be used in nested sequences. """
        with pytest.raises(AssertionError) as exc_info:
            assert list(parser.generate_commands(yaml.load("""
                - - foreach: my_series:A,B
                  - - foreach: my_series:1,2
                    - echo test{{my_series}}
            """)))

    def test_foreach_in_non_first_position_raises_error(self):
        """ 'Foreach' can only be specified at the beginning of a sequence. """
        with pytest.raises(AssertionError) as exc_info:
            list(parser.generate_commands(yaml.load("""
                - something
                - foreach: [A,B]
                """)))
        assert ("'foreach' may only be specified at the beginning of a sequence" in
                str(exc_info.value))

    def test_foreach_series_with_integer_feature_values(self):
        """ Sequences are repeated for each item in the 'foreach' series. """
        assert list(parser.generate_commands(yaml.load("""
            - foreach: [A,B]
            - echo test{{A,B}}:
                retries: 1
        """))) == [('echo testA', {'retries': 1}), ('echo testB', {'retries': 1})]

    def test_foreach_series_with_features(self):
        """ Sequences are repeated for each item in the 'foreach' series. """
        assert list(parser.generate_commands(yaml.load("""
            - foreach: [A,B]
            - echo test{{A,B}}:
                depends_on: pre{{A,B}}
        """))) == [('echo testA', {'depends_on': 'preA'}), ('echo testB', {'depends_on': 'preB'})]

