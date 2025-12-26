"""JVM repository indexers using SCIP protocol."""

from cicada.languages.scip.configurable_indexer import ConfigurableSCIPIndexer


class JavaSCIPIndexer(ConfigurableSCIPIndexer):
    """Index Java repositories using scip-java."""

    def __init__(self, verbose: bool = False):
        super().__init__("java", verbose)


class ScalaSCIPIndexer(ConfigurableSCIPIndexer):
    """Index Scala repositories using scip-java."""

    def __init__(self, verbose: bool = False):
        super().__init__("scala", verbose)
