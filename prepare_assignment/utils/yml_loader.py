from ruamel.yaml import YAML

YAML_LOADER = YAML(typ='safe')
YAML_LOADER.brace_single_entry_mapping_in_flow_sequence = False
YAML_LOADER.default_flow_style = True