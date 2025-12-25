# Java + coursier complete environment
# Includes Java JDK and coursier (for scip-java fallback)

FROM cicada-base

# Install Java
RUN apt-get update && apt-get install -y \
    default-jdk \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Gradle (Debian package is too old for Java 21)
ENV GRADLE_VERSION=8.11.1
RUN curl -fL "https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip" -o gradle.zip && \
    unzip gradle.zip -d /opt && \
    rm gradle.zip && \
    ln -s /opt/gradle-${GRADLE_VERSION}/bin/gradle /usr/local/bin/gradle

# Install Coursier (used by JVM indexer for scip-java fallback)
# Use JAR file for cross-platform support (no native arm64 Linux binary available)
RUN curl -fLo /usr/local/lib/coursier.jar "https://github.com/coursier/coursier/releases/latest/download/coursier.jar" && \
    echo '#!/bin/sh\nexec java -jar /usr/local/lib/coursier.jar "$@"' > /usr/local/bin/cs && \
    chmod +x /usr/local/bin/cs

# Verify coursier is installed
RUN cs --help > /dev/null 2>&1 && echo "✓ coursier installed"

WORKDIR /workspace
