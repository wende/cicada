"""C/C++ repository indexers using SCIP protocol."""

from cicada.languages.scip.configurable_indexer import ConfigurableSCIPIndexer


class CSCIPIndexer(ConfigurableSCIPIndexer):
    """Index C repositories using scip-clang."""

    def __init__(self, verbose: bool = False):
        super().__init__("c", verbose)


class CppSCIPIndexer(ConfigurableSCIPIndexer):
    """Index C++ repositories using scip-clang."""

    def __init__(self, verbose: bool = False):
        super().__init__("cpp", verbose)
