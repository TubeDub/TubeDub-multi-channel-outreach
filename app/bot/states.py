from enum import IntEnum

class WizardState(IntEnum):
    PLATFORM = 0
    CAMPAIGN_TYPE = 1
    COUNTRY = 2
    CITY = 3
    AUDIENCE_SOURCE = 4
    AUDIENCE_MODE = 5
    MESSAGE_TEXT = 6
    LINK = 7
    SCHEDULE = 8
    PREVIEW = 9
    EDIT_FIELD = 10  # for editing existing campaign
