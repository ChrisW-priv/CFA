from SimCFA.configs import execute_config_from_file, manual_config, save_states_and_print_run


def main(filename: str):
    if filename:
        execute_config_from_file(filename, save_states_and_print_run)
        return
    manual_config()


if __name__ == "__main__":
    filename = r"C:\Users\kwatras\Projects\CFA\SimCFA\data\example_simulation_config01.json"
    main(filename)
