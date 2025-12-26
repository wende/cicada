"""Ruby repository indexer using SCIP protocol."""

from cicada.languages.scip.configurable_indexer import ConfigurableSCIPIndexer


class RubySCIPIndexer(ConfigurableSCIPIndexer):
    """Index Ruby repositories using scip-ruby."""

    def __init__(self, verbose: bool = False):
        super().__init__("ruby", verbose)
