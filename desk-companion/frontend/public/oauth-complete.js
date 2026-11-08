// Only the account-authorization popup is closed. The opener reads its own
// authenticated application status; OAuth codes/tokens never cross postMessage.
if (window.opener) window.close();
