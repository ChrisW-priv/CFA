def compound_interest_calc(percent, years, n_times_during_year=1):
    """
    Calculates "how much money will I make with 1000 USD"

    :param percent:
    :param years:
    :param n_times_during_year:
    :return:
    """
    ORIGINAL = 1
    exponent = 1 + (percent / 100) / n_times_during_year
    periods = (years*n_times_during_year)
    multiplier = exponent ** periods
    return ORIGINAL * multiplier


def principal_amount_calc(percent, years, n_times_during_year=1):
    """
    Calculates "how much money do I need to make 1000 USD"

    :param percent:
    :param years:
    :param n_times_during_year:
    :return:
    """
    ACCURED = 1
    exponent = 1 + (percent / 100) / n_times_during_year
    periods = (years*n_times_during_year)
    multiplier = exponent ** periods
    return ACCURED / multiplier


def rate_of_interest_calc(percent, years, n_times_during_year=1):
    """
    Calculates "What percentage do I need to target to get 'percentage' return"

    :param percent:
    :param years:
    :param n_times_during_year:
    :return:
    """
    ORIGINAL = 1
    accured = ORIGINAL * (1 + (percent / 100))
    a_div_p = accured / ORIGINAL
    periods = (years * n_times_during_year)
    exponent = 1 / periods
    x = a_div_p ** exponent
    x -= 1
    x *= n_times_during_year
    return x
