# Scala + sbt + coursier complete environment
# Includes Java, sbt, and coursier (for scip-java fallback)

FROM cicada-base

# Install Java
RUN apt-get update && apt-get install -y \
    default-jdk \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install sbt
RUN echo "deb https://repo.scala-sbt.org/scalasbt/debian all main" | tee /etc/apt/sources.list.d/sbt.list \
    && curl -sL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x2EE0EA64E40A89B84B2DF73499E82A75642AC823" | gpg --dearmor -o /etc/apt/trusted.gpg.d/sbt.gpg \
    && apt-get update && apt-get install -y sbt \
    && rm -rf /var/lib/apt/lists/*

# Install Coursier (used by JVM indexer for scip-java fallback)
# Use JAR file for cross-platform support (no native arm64 Linux binary available)
RUN curl -fLo /usr/local/lib/coursier.jar "https://github.com/coursier/coursier/releases/latest/download/coursier.jar" && \
    echo '#!/bin/sh\nexec java -jar /usr/local/lib/coursier.jar "$@"' > /usr/local/bin/cs && \
    chmod +x /usr/local/bin/cs

# Verify installations
RUN sbt --version > /dev/null 2>&1 && echo "✓ sbt installed"
RUN cs --help > /dev/null 2>&1 && echo "✓ coursier installed"

WORKDIR /workspace
