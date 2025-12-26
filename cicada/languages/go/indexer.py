"""Go repository indexer using SCIP protocol."""

from cicada.languages.scip.configurable_indexer import ConfigurableSCIPIndexer


class GoSCIPIndexer(ConfigurableSCIPIndexer):
    """Index Go repositories using scip-go."""

    def __init__(self, verbose: bool = False):
        super().__init__("go", verbose)
