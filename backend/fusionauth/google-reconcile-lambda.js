/**
 * FusionAuth Google Reconcile Lambda for Quien.uy
 *
 * Purpose:
 *   Copies the latest Google profile claims into the FusionAuth User
 *   on every federated Google login. This ensures that when a user
 *   changes their Google profile picture, the new URL is persisted
 *   in FusionAuth and subsequently returned by /oauth2/userinfo and
 *   the ID token.
 *
 * How to install:
 *   1. In the FusionAuth admin UI, go to Settings > Lambdas.
 *   2. Click "Add" to create a new Lambda.
 *   3. Set the Name to "Google Reconcile - Quien.uy".
 *   4. Set the Type to "Reconcile".
 *   5. Paste this entire script into the Body field.
 *   6. Save the Lambda.
 *   7. Go to Settings > Identity Providers > Google.
 *   8. Under the "Reconcile" section, select the Lambda you just created.
 *   9. Save the Identity Provider configuration.
 *
 * What this Lambda does:
 *   - On every Google login, copies idToken.given_name, family_name,
 *     name, and picture into the FusionAuth User object.
 *   - Specifically, user.imageUrl is set to idToken.picture (or null
 *     if Google no longer provides a picture).
 *   - This ensures the Quien.uy backend always receives the latest
 *     Google profile image URL via /oauth2/userinfo and the ID token.
 *
 * Important notes:
 *   - This Lambda runs AFTER FusionAuth has already processed the
 *     Google login. It modifies the in-memory User object before
 *     FusionAuth persists it.
 *   - If the user has manually overridden their imageUrl in FusionAuth,
 *     this Lambda will overwrite it with the Google value on every
 *     Google login. This is the desired behavior for Quien.uy.
 *   - The "picture" claim in Google's ID token is a URL to the user's
 *     profile photo. It may contain query parameters (e.g., size hints).
 *     This Lambda passes it through as-is — do not modify the URL.
 *
 * @param {Object} user - The FusionAuth User object (mutable).
 * @param {Object} registration - The UserRegistration for this IdP.
 * @param {Object} idToken - The parsed Google ID token claims.
 * @param {Object} context - Additional context from the IdP login.
 */
function reconcile(user, registration, idToken, context) {
  // Refresh the user's first name from Google.
  if (idToken.given_name) {
    user.firstName = idToken.given_name;
  }

  // Refresh the user's last name from Google.
  if (idToken.family_name) {
    user.lastName = idToken.family_name;
  }

  // Refresh the user's full display name from Google.
  if (idToken.name) {
    user.fullName = idToken.name;
  }

  // Refresh the Google profile image on every federated login.
  // Clear a previously persisted invalid value when Google no longer
  // provides a picture.
  user.imageUrl = idToken.picture || null;
}
