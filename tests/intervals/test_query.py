from registered.intervals.query import sql


class TestSql:
    def test_same_number_of_question_marks(self):
        where = "field = ? OR field = ?"
        parameters = [1, 2]
        (formatted, formatted_parameters) = sql(where, parameters)

        expected = len(formatted_parameters)
        actual = formatted.count("?")

        assert expected == actual

    def test_no_parameters(self):
        where = "1=1"
        formatted = sql(where)

        assert isinstance(formatted, str)
