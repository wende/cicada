# 📚 Complete Workflow Examples

These examples show how to chain tools together to understand and modify your codebase effectively.

## Pro Tips

- 🔍 **Don't know exact names?** → Use `search_by_features` with concepts like "authentication", "api key storage", "tab navigation"
- 📖 **Understanding "why"?** → Combine code search with `get_file_pr_history` to see design discussions
- 🎯 **Wildcards work!** → In `search_by_features`, use patterns like `create*`, `*_user`, or `validate_*`
- 🔗 **Chain tools together** → `search_by_features` → `search_function` → `get_file_pr_history` gives you the full picture

## Example 1: Adding a New Feature

**User Request:** "Add API key management to the user settings page"

**Workflow:**

```
Step 1: Find how API keys are currently handled
→ search_by_features("api key storage encryption")
   Found: App.Vault.encrypt/1, App.Credentials schema

Step 2: Understand the security approach
→ get_file_pr_history("lib/app/vault.ex")
   PR #145: "Add encrypted credential storage"
   💬 @security: "Using AES-256-GCM, keys stored in credentials table"
   💬 @reviewer: "Never store in session, always in DB"

Step 3: Find the user settings LiveView
→ search_by_features("user settings liveview")
   Found: AppWeb.UserSettingsLive

Step 4: See how existing tabs are implemented
→ search_function("render*tab", path: "lib/app_web/live/user_settings_live.ex")
   Found: render_tab/1 pattern used for navigation

Step 5: Find where Vault is already used
→ search_function("Vault.encrypt")
   Called in: UserController.create/2, ApiController.store_key/2

→ Now you have everything: security pattern, UI structure, and usage examples!
```

## Example 2: Understanding a Bug

**User Request:** "Users are reporting authentication failures after password reset"

**Workflow:**

```
Step 1: Find authentication-related code
→ search_by_features("password reset authentication")
   Found: Auth.reset_password/2, UserAuth.verify_credentials/2

Step 2: Check the password reset function
→ search_function("reset_password")
   Defined in: lib/app/auth.ex:87
   Called from: UserController.reset_password/2, AuthController.confirm_reset/2

Step 3: Understand why it was implemented this way
→ get_file_pr_history("lib/app/auth.ex")
   PR #234: "Add password reset flow"
   💬 @reviewer: "Must invalidate all sessions on password change"
   💬 @author: "Added session cleanup in reset_password/2"

Step 4: Check if session cleanup is actually happening
→ search_function("invalidate_sessions")
   Found: Auth.invalidate_sessions/1
   Called from: Auth.reset_password/2 (line 92)

Step 5: Look at recent changes
→ get_commit_history("lib/app/auth.ex", function: "reset_password")
   Last modified: 2 weeks ago, PR #256 "Optimize session queries"
   → Check if optimization broke session invalidation!
```

## Example 3: Refactoring Safely

**User Request:** "I want to rename `create_user/2` to `register_user/2`"

**Workflow:**

```
Step 1: Find all definitions
→ search_function("create_user/2")
   Defined in: lib/app/accounts.ex:42

Step 2: Find everywhere it's called
→ search_function("create_user/2")
   Called from 12 locations:
   - UserController.create/2 (controllers/user_controller.ex:15)
   - ApiController.register/2 (controllers/api_controller.ex:28)
   - RegistrationLive.save/2 (live/registration_live.ex:67)
   [... 9 more]

Step 3: Check if it's part of a public API
→ search_module("App.Accounts")
   Public functions: create_user/2, update_user/2, delete_user/2
   → Yes, it's in the public API!

Step 4: Check module usage to see external dependencies
→ search_module_usage("App.Accounts")
   Used in 8 files across controllers, LiveViews, and tests

Step 5: Check PR history for context
→ get_file_pr_history("lib/app/accounts.ex")
   PR #12: "Initial accounts context"
   💬 @lead: "Follow Phoenix conventions for context functions"
   → If renaming, should we keep `create_*` convention?
```

## Example 4: Finding Cleanup Opportunities

**User Request:** "Find unused code we can remove"

**Workflow:**

```
Step 1: Find high-confidence dead code
→ find_dead_code(min_confidence: "high")
   Found 8 functions:
   - App.Utils.legacy_format_date/1 (created 2 years ago)
   - App.Cache.clear_v1/0 (created 18 months ago)

Step 2: Verify with git history
→ get_commit_history("lib/app/utils.ex", function: "legacy_format_date")
   Created: PR #45 "Add date formatting" (2 years ago)
   Last modified: Same PR (never updated since)

Step 3: Check the PR context
→ get_file_pr_history("lib/app/utils.ex")
   PR #45: "Add date formatting"
   💬 @reviewer: "Let's use Timex.format instead"
   PR #156: "Switch to Timex" (1.5 years ago)
   💬 @author: "Replaced legacy_format_date with Timex"
   → Confirmed: replaced but never removed!

Step 4: Double-check it's really unused
→ search_function("legacy_format_date")
   Defined in: lib/app/utils.ex:123
   Called from: (no call sites found)
   → Safe to remove!
```

## Example 5: Learning a New Codebase

**User Request:** "I'm new to this codebase, help me understand the authentication system"

**Workflow:**

```
Step 1: Find authentication-related code
→ search_by_features("authentication login session")
   Found modules: App.Auth, AppWeb.UserAuth, AppWeb.AuthController
   Found functions: authenticate/2, verify_credentials/2, create_session/2

Step 2: Start with the main auth module
→ search_module("App.Auth")
   Public functions:
   - authenticate(email, password) :: {:ok, user} | {:error, reason}
   - verify_credentials(user, password) :: boolean
   - create_session(conn, user) :: conn
   - invalidate_sessions(user) :: :ok

Step 3: Understand the design decisions
→ get_file_pr_history("lib/app/auth.ex")
   PR #12: "Initial authentication system"
   💬 @security: "Using bcrypt with cost factor 12"
   💬 @lead: "Session tokens stored in DB, not JWT"

   PR #89: "Add session expiration"
   💬 @reviewer: "Expire after 30 days of inactivity"

Step 4: See real usage examples
→ search_function("Auth.authenticate")
   Called in:
   - AuthController.login/2 → HTTP login endpoint
   - ApiController.token/2 → API authentication
   - SessionLive.verify/2 → LiveView authentication

Step 5: Check for gotchas in commit history
→ get_commit_history("lib/app/auth.ex")
   23 commits total
   Recent: "Fix timing attack in password comparison" (PR #234)
   → Important security fix to know about!
```

## Key Takeaways

1. **Start broad, then narrow:** Use `search_by_features` to find relevant code, then `search_function` for details
2. **Always check PR history:** `get_file_pr_history` reveals *why* code exists and design decisions
3. **Verify before refactoring:** Use `search_function` to find all call sites before renaming
4. **Chain tools together:** Each tool provides context for the next step
5. **When stuck:** Try `search_by_features` with different concepts - it's more powerful than you think!
