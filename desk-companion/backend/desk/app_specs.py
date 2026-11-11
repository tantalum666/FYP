"""Bundled app manifests. Remote descriptions cannot add permissions or destinations."""

GOOGLE_SEND = "https://www.googleapis.com/auth/gmail.send"
SPECS = {
    "gmail": {
        "name": "Gmail",
        "provider": "google",
        "scopes": (
            "openid",
            "email",
            GOOGLE_SEND,
            "https://www.googleapis.com/auth/gmail.readonly",
        ),
        "callback": "/api/apps/gmail/callback",
        "capabilities": ("email_read", "email_send"),
    },
    "calendar": {
        "name": "Google Calendar",
        "provider": "google",
        "scopes": ("https://www.googleapis.com/auth/calendar.events.readonly",),
        "callback": "/api/google/callback",
        "capabilities": ("calendar_read",),
    },
    "microsoft365": {
        "name": "Microsoft 365",
        "provider": "microsoft",
        "scopes": (
            "openid",
            "email",
            "offline_access",
            "User.Read",
            "Mail.Read",
            "Mail.Send",
            "Calendars.Read",
            "Files.Read",
            "Tasks.Read",
            "Notes.Read",
        ),
        "callback": "/api/apps/microsoft/callback",
        "capabilities": (
            "outlook_mail",
            "outlook_calendar",
            "onedrive",
            "word",
            "excel",
            "powerpoint",
            "todo",
            "onenote",
        ),
    },
    "teams": {
        "name": "Microsoft Teams",
        "provider": "microsoft",
        "scopes": ("openid", "email", "offline_access", "User.Read", "Chat.Read"),
        "callback": "/api/apps/microsoft/callback",
        "organization_only": True,
        "capabilities": ("teams_read",),
    },
    "sharepoint": {
        "name": "SharePoint",
        "provider": "microsoft",
        "scopes": ("openid", "email", "offline_access", "User.Read", "Sites.Read.All"),
        "callback": "/api/apps/microsoft/callback",
        "organization_only": True,
        "capabilities": ("sharepoint_read",),
    },
}
SCOPES = {key: value["scopes"] for key, value in SPECS.items()}
CALLBACKS = {key: value["callback"] for key, value in SPECS.items()}
