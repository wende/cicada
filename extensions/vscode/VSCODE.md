# VSCode Marketplace Extension Guide

## Overview

**Platform:** https://marketplace.visualstudio.com
**Audience:** Millions of VSCode users
**Submission Time:** 6-8 hours (initial), 1-2 hours (updates)
**Approval Time:** Automated (instant for verified publishers)
**Maintenance:** Moderate (version updates, compatibility testing)

**Complexity:** ⭐⭐⭐ High - Requires TypeScript extension wrapper

---

## Prerequisites

### Required Tools
- [ ] Node.js 18+ and npm/yarn
- [ ] VSCode Extension development knowledge
- [ ] TypeScript familiarity
- [ ] Azure DevOps account (for publishing)
- [ ] Python installed (for cicada)

### Required Assets
- [ ] Extension icon (128x128 PNG)
- [ ] Extension logo (512x512 PNG optional)
- [ ] Screenshots (1280x800 recommended)
- [ ] Demo GIF or video
- [ ] README with clear installation instructions

---

## Architecture Overview

VSCode extensions for MCP servers work by:
1. Extension activates on workspace open
2. Extension registers MCP server in VSCode settings
3. VSCode's MCP support loads the server
4. Extension can provide UI for setup/config

**Key Files:**
```
extensions/vscode/
├── package.json          # Extension manifest
├── src/
│   ├── extension.ts      # Entry point
│   ├── setup.ts          # First-time setup logic
│   └── statusBar.ts      # Status bar integration
├── icon.png              # Extension icon (128x128)
├── README.md             # Marketplace description
├── CHANGELOG.md          # Version history
└── tsconfig.json         # TypeScript config
```

---

## Step-by-Step Implementation

### Phase 1: Extension Scaffold

#### 1.1 Install Extension Generator
```bash
npm install -g yo generator-code
```

#### 1.2 Generate Extension
```bash
cd extensions/vscode
yo code

# Select:
# - New Extension (TypeScript)
# - Name: cicada
# - Identifier: cicada
# - Description: "Elixir code intelligence via MCP"
# - Initialize git: No (already in repo)
# - Package manager: npm
```

#### 1.3 Update package.json

**Add MCP server registration:**
```json
{
  "name": "cicada",
  "displayName": "Cicada - Elixir Code Intelligence",
  "description": "Intelligent code search and analysis for Elixir projects",
  "version": "0.2.0",
  "publisher": "wende",
  "engines": {
    "vscode": "^1.102.0"
  },
  "categories": [
    "Programming Languages",
    "Other"
  ],
  "activationEvents": [
    "onLanguage:elixir",
    "workspaceContains:**/*.ex"
  ],
  "main": "./out/extension.js",
  "contributes": {
    "mcp": {
      "servers": [
        {
          "id": "cicada",
          "name": "Cicada",
          "command": "cicada-mcp"
        }
      ]
    },
    "commands": [
      {
        "command": "cicada.setup",
        "title": "Cicada: Setup Project"
      },
      {
        "command": "cicada.reindex",
        "title": "Cicada: Re-index Project"
      }
    ],
    "configuration": {
      "title": "Cicada",
      "properties": {
        "cicada.autoIndex": {
          "type": "boolean",
          "default": true,
          "description": "Automatically index workspace on open"
        }
      }
    }
  },
  "scripts": {
    "vscode:prepublish": "npm run compile",
    "compile": "tsc -p ./",
    "watch": "tsc -watch -p ./",
    "package": "vsce package"
  },
  "devDependencies": {
    "@types/vscode": "^1.102.0",
    "@types/node": "20.x",
    "typescript": "^5.6.0",
    "@vscode/vsce": "^3.0.0"
  }
}
```

### Phase 2: Extension Logic

#### 2.1 Create src/extension.ts
```typescript
import * as vscode from 'vscode';
import { checkCicadaInstalled, setupProject, reindexProject } from './setup';
import { CicadaStatusBar } from './statusBar';

export async function activate(context: vscode.ExtensionContext) {
    console.log('Cicada extension activating...');

    const statusBar = new CicadaStatusBar();
    context.subscriptions.push(statusBar);

    // Check if cicada is installed
    const isInstalled = await checkCicadaInstalled();
    if (!isInstalled) {
        const choice = await vscode.window.showWarningMessage(
            'Cicada is not installed. Install it to enable Elixir code intelligence.',
            'Install Now',
            'Later'
        );

        if (choice === 'Install Now') {
            await installCicada();
        }
        return;
    }

    // Check if workspace needs setup
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (workspaceFolder) {
        const needsSetup = await checkNeedsSetup(workspaceFolder.uri.fsPath);

        if (needsSetup) {
            const autoIndex = vscode.workspace.getConfiguration('cicada').get('autoIndex');

            if (autoIndex) {
                await setupProject(workspaceFolder.uri.fsPath, statusBar);
            } else {
                showSetupPrompt(workspaceFolder.uri.fsPath, statusBar);
            }
        }
    }

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('cicada.setup', async () => {
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            if (workspaceFolder) {
                await setupProject(workspaceFolder.uri.fsPath, statusBar);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('cicada.reindex', async () => {
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            if (workspaceFolder) {
                await reindexProject(workspaceFolder.uri.fsPath, statusBar);
            }
        })
    );

    console.log('Cicada extension activated');
}

export function deactivate() {}

async function installCicada(): Promise<void> {
    const terminal = vscode.window.createTerminal('Cicada Installation');
    terminal.show();
    terminal.sendText('uv tool install git+https://github.com/wende/cicada.git@latest');

    vscode.window.showInformationMessage(
        'Installing Cicada... Please restart VSCode when complete.'
    );
}

async function checkNeedsSetup(workspacePath: string): Promise<boolean> {
    const fs = require('fs');
    const path = require('path');

    const configPath = path.join(workspacePath, '.cicada', 'config.yaml');
    return !fs.existsSync(configPath);
}

function showSetupPrompt(workspacePath: string, statusBar: CicadaStatusBar): void {
    vscode.window.showInformationMessage(
        'Cicada needs to index this project. Run setup now?',
        'Setup Now',
        'Later'
    ).then(choice => {
        if (choice === 'Setup Now') {
            setupProject(workspacePath, statusBar);
        }
    });
}
```

#### 2.2 Create src/setup.ts
```typescript
import * as vscode from 'vscode';
import { spawn } from 'child_process';
import { CicadaStatusBar } from './statusBar';

export async function checkCicadaInstalled(): Promise<boolean> {
    return new Promise((resolve) => {
        const child = spawn('which', ['cicada']);
        child.on('close', (code) => {
            resolve(code === 0);
        });
    });
}

export async function setupProject(
    workspacePath: string,
    statusBar: CicadaStatusBar
): Promise<void> {
    statusBar.setIndexing();

    return vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Cicada: Indexing project',
        cancellable: false
    }, async (progress) => {
        progress.report({ message: 'Setting up...' });

        return new Promise<void>((resolve, reject) => {
            const child = spawn('cicada', [workspacePath]);

            child.stdout.on('data', (data) => {
                const message = data.toString();
                console.log('Cicada:', message);
                progress.report({ message });
            });

            child.stderr.on('data', (data) => {
                console.error('Cicada error:', data.toString());
            });

            child.on('close', (code) => {
                if (code === 0) {
                    statusBar.setReady();
                    vscode.window.showInformationMessage('Cicada setup complete!');
                    resolve();
                } else {
                    statusBar.setError();
                    vscode.window.showErrorMessage('Cicada setup failed');
                    reject(new Error(`Setup failed with code ${code}`));
                }
            });
        });
    });
}

export async function reindexProject(
    workspacePath: string,
    statusBar: CicadaStatusBar
): Promise<void> {
    statusBar.setIndexing();

    return vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Cicada: Re-indexing',
        cancellable: false
    }, async (progress) => {
        return new Promise<void>((resolve, reject) => {
            const child = spawn('cicada', ['index'], { cwd: workspacePath });

            child.stdout.on('data', (data) => {
                progress.report({ message: data.toString() });
            });

            child.on('close', (code) => {
                if (code === 0) {
                    statusBar.setReady();
                    vscode.window.showInformationMessage('Re-indexing complete!');
                    resolve();
                } else {
                    statusBar.setError();
                    reject(new Error(`Re-index failed with code ${code}`));
                }
            });
        });
    });
}
```

#### 2.3 Create src/statusBar.ts
```typescript
import * as vscode from 'vscode';

export class CicadaStatusBar {
    private statusBarItem: vscode.StatusBarItem;

    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.statusBarItem.command = 'cicada.reindex';
        this.setReady();
        this.statusBarItem.show();
    }

    setReady(): void {
        this.statusBarItem.text = '$(cicada) Cicada: Ready';
        this.statusBarItem.tooltip = 'Click to re-index';
        this.statusBarItem.backgroundColor = undefined;
    }

    setIndexing(): void {
        this.statusBarItem.text = '$(sync~spin) Cicada: Indexing...';
        this.statusBarItem.tooltip = 'Indexing in progress';
        this.statusBarItem.command = undefined;
    }

    setError(): void {
        this.statusBarItem.text = '$(error) Cicada: Error';
        this.statusBarItem.tooltip = 'Setup failed. Click to retry.';
        this.statusBarItem.backgroundColor = new vscode.ThemeColor(
            'statusBarItem.errorBackground'
        );
        this.statusBarItem.command = 'cicada.setup';
    }

    dispose(): void {
        this.statusBarItem.dispose();
    }
}
```

### Phase 3: Publishing Setup

#### 3.1 Create Azure DevOps Account
1. Go to https://dev.azure.com
2. Sign in with Microsoft account
3. Create organization (e.g., "wende-dev")

#### 3.2 Create Publisher
1. Go to https://marketplace.visualstudio.com/manage
2. Click "Create publisher"
3. ID: "wende" (must be unique)
4. Name: "Wende"
5. Add personal access token from Azure DevOps

#### 3.3 Generate Personal Access Token
1. In Azure DevOps, click user icon → Personal Access Tokens
2. Create new token:
   - Name: "vscode-marketplace"
   - Organization: All accessible organizations
   - Scopes: Marketplace → Manage
   - Expiration: 1 year
3. Copy token (you won't see it again!)

#### 3.4 Login to vsce
```bash
npm install -g @vscode/vsce
vsce login wende
# Paste your personal access token
```

### Phase 4: Package and Publish

#### 4.1 Build Extension
```bash
cd extensions/vscode
npm install
npm run compile
```

#### 4.2 Create VSIX Package
```bash
vsce package
# Creates cicada-0.2.0.vsix
```

#### 4.3 Test Locally
```bash
code --install-extension cicada-0.2.0.vsix
# Restart VSCode
# Open Elixir project
# Test commands and MCP integration
```

#### 4.4 Publish to Marketplace
```bash
vsce publish
# Or with specific version
vsce publish 0.2.0
```

---

## Marketplace Listing Optimization

### README.md for Marketplace
```markdown
# Cicada - Elixir Code Intelligence

Powerful code search and analysis for Elixir projects, powered by the Model Context Protocol (MCP).

## Features

✨ **Instant Module Search** - Find any Elixir module and view its complete API
🔍 **Function Discovery** - Locate function definitions across your entire codebase
📍 **Call Site Analysis** - See where functions are called with code context
📜 **Git Integration** - Discover PR attribution, commit history, and authorship
🎯 **Dead Code Detection** - Find potentially unused functions
⚡ **Lightning Fast** - Index your project in seconds

## Quick Start

1. Install the extension
2. Open an Elixir/Phoenix project
3. Cicada will automatically index your codebase
4. Ask Copilot:
   - "Show me the User module"
   - "Where is authenticate/2 called?"
   - "Who wrote this line of code?"

## Requirements

- VSCode 1.102+
- Python 3.10+
- Elixir project

The extension will guide you through installing the Cicada CLI if needed.

## Extension Settings

* `cicada.autoIndex`: Automatically index workspace on open (default: true)

## Commands

* `Cicada: Setup Project` - Initialize Cicada for current workspace
* `Cicada: Re-index Project` - Update the code index

## Known Issues

See [GitHub Issues](https://github.com/wende/cicada/issues) for known problems.

## Release Notes

### 0.2.0
- Initial VSCode Marketplace release
- Automatic indexing on project open
- Status bar integration
- Setup wizard

---

**Enjoy intelligent Elixir code search!**
```

### Icon Requirements
- **Size:** 128x128 pixels
- **Format:** PNG
- **Style:** Simple, recognizable at small sizes
- **Background:** Transparent or solid color
- **Location:** `extensions/vscode/icon.png`

---

## Testing Checklist

Before publishing:

- [ ] Extension activates on Elixir project open
- [ ] Setup wizard works for fresh project
- [ ] Re-index command works
- [ ] Status bar updates correctly
- [ ] Commands appear in command palette
- [ ] MCP server starts successfully
- [ ] Copilot can use Cicada tools
- [ ] Works on Windows/Mac/Linux
- [ ] Error messages are helpful
- [ ] README renders correctly in marketplace

---

## Maintenance Strategy

### Version Updates
```bash
# Update version in package.json
npm version patch  # or minor, or major

# Rebuild and test
npm run compile
vsce package

# Test locally
code --install-extension cicada-0.2.1.vsix

# Publish
vsce publish
```

### Monitoring
- Check marketplace analytics monthly
- Monitor GitHub issues tagged with `[vscode]`
- Test on new VSCode versions
- Keep dependencies updated

---

## Estimated Effort

| Phase | Time | Complexity |
|-------|------|------------|
| Extension scaffold | 2 hours | Medium |
| Core logic | 3 hours | Medium |
| UI/UX polish | 2 hours | Low |
| Testing | 2 hours | Medium |
| Marketplace setup | 1 hour | Low |
| **Total** | **10 hours** | **Medium** |

---

## Future Enhancements

### v0.3
- [ ] Settings UI for keyword extraction
- [ ] Progress bar for indexing
- [ ] TreeView for module explorer
- [ ] Inline code lens with usage counts
- [ ] Quick pick for module search

### v0.4
- [ ] WebView for advanced search UI
- [ ] Diff view for PR history
- [ ] Graph view for dependencies
- [ ] Integration with testing frameworks

---

**Status:** 📝 Design Complete, Implementation Pending
**Priority:** Medium (defer to post-MVP)
**Next Action:** Create extension scaffold after PyPI publishing
