""".NET repository indexers using SCIP protocol."""

from cicada.languages.scip.configurable_indexer import ConfigurableSCIPIndexer


class CSharpSCIPIndexer(ConfigurableSCIPIndexer):
    """Index C# repositories using scip-dotnet."""

    def __init__(self, verbose: bool = False):
        super().__init__("csharp", verbose)


class VBSCIPIndexer(ConfigurableSCIPIndexer):
    """Index Visual Basic repositories using scip-dotnet."""

    def __init__(self, verbose: bool = False):
        super().__init__("vb", verbose)
