"""Dart repository indexer using SCIP protocol."""

from cicada.languages.scip.configurable_indexer import ConfigurableSCIPIndexer


class DartSCIPIndexer(ConfigurableSCIPIndexer):
    """Index Dart repositories using scip-dart."""

    def __init__(self, verbose: bool = False):
        super().__init__("dart", verbose)
