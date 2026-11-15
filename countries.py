"""Every country by ISO code, for feeds that give only a code ("cn", "AU") and for the flag rule (AGENT_NOTES.md, "Flags").

NAMES: ISO 3166-1 alpha-2 code -> the short English name a reader expects ("Russia", not "Russian Federation").
name(code) returns "" for an unknown code, never a guess.
"""

_RAW = """AD Andorra|AE United Arab Emirates|AF Afghanistan|AG Antigua and Barbuda|AL Albania|AM Armenia|AO Angola|AR Argentina|AT Austria|
AU Australia|AZ Azerbaijan|BA Bosnia and Herzegovina|BB Barbados|BD Bangladesh|BE Belgium|BF Burkina Faso|BG Bulgaria|BH Bahrain|BI Burundi|
BJ Benin|BN Brunei|BO Bolivia|BR Brazil|BS Bahamas|BT Bhutan|BW Botswana|BY Belarus|BZ Belize|CA Canada|CD DR Congo|CF Central African Republic|
CG Congo|CH Switzerland|CI Côte d'Ivoire|CL Chile|CM Cameroon|CN China|CO Colombia|CR Costa Rica|CU Cuba|CV Cape Verde|CY Cyprus|CZ Czechia|
DE Germany|DJ Djibouti|DK Denmark|DM Dominica|DO Dominican Republic|DZ Algeria|EC Ecuador|EE Estonia|EG Egypt|ER Eritrea|ES Spain|ET Ethiopia|
FI Finland|FJ Fiji|FR France|GA Gabon|GB United Kingdom|GD Grenada|GE Georgia|GH Ghana|GM Gambia|GN Guinea|GQ Equatorial Guinea|GR Greece|
GT Guatemala|GW Guinea-Bissau|GY Guyana|HK Hong Kong|HN Honduras|HR Croatia|HT Haiti|HU Hungary|ID Indonesia|IE Ireland|IL Israel|IN India|
IQ Iraq|IR Iran|IS Iceland|IT Italy|JM Jamaica|JO Jordan|JP Japan|KE Kenya|KG Kyrgyzstan|KH Cambodia|KM Comoros|KN Saint Kitts and Nevis|
KR South Korea|KW Kuwait|KZ Kazakhstan|LA Laos|LB Lebanon|LC Saint Lucia|LI Liechtenstein|LK Sri Lanka|LR Liberia|LS Lesotho|LT Lithuania|
LU Luxembourg|LV Latvia|LY Libya|MA Morocco|MC Monaco|MD Moldova|ME Montenegro|MG Madagascar|MK North Macedonia|ML Mali|MM Myanmar|MN Mongolia|
MO Macau|MR Mauritania|MT Malta|MU Mauritius|MV Maldives|MW Malawi|MX Mexico|MY Malaysia|MZ Mozambique|NA Namibia|NE Niger|NG Nigeria|
NI Nicaragua|NL Netherlands|NO Norway|NP Nepal|NZ New Zealand|OM Oman|PA Panama|PE Peru|PG Papua New Guinea|PH Philippines|PK Pakistan|
PL Poland|PR Puerto Rico|PS Palestine|PT Portugal|PY Paraguay|QA Qatar|RO Romania|RS Serbia|RU Russia|RW Rwanda|SA Saudi Arabia|SC Seychelles|
SD Sudan|SE Sweden|SG Singapore|SI Slovenia|SK Slovakia|SL Sierra Leone|SM San Marino|SN Senegal|SO Somalia|SR Suriname|SS South Sudan|
SV El Salvador|SY Syria|SZ Eswatini|TD Chad|TG Togo|TH Thailand|TJ Tajikistan|TL Timor-Leste|TM Turkmenistan|TN Tunisia|TR Türkiye|
TT Trinidad and Tobago|TW Taiwan|TZ Tanzania|UA Ukraine|UG Uganda|US United States|UY Uruguay|UZ Uzbekistan|VE Venezuela|VN Vietnam|
XK Kosovo|YE Yemen|ZA South Africa|ZM Zambia|ZW Zimbabwe"""

NAMES = dict(x.strip().split(" ", 1) for x in _RAW.replace("\n", "").split("|"))
# What feeds write instead of the short name (German, Russian and official forms), so a written-out country is still recognised.
OTHER_NAMES = {
    "RU": "russian federation|россия|российская федерация|russland", "KZ": "казахстан|qazaqstan", "BY": "беларусь|belarus", "UZ": "узбекистан|o'zbekiston",
    "KG": "кыргызстан|киргизия|kyrgyz republic", "AM": "армения", "GE": "грузия", "AZ": "азербайджан", "MD": "молдова|moldavia", "TJ": "таджикистан",
    "CZ": "czech republic", "TR": "turkey", "CI": "ivory coast", "CD": "democratic republic of the congo", "MK": "macedonia", "SZ": "swaziland",
    "LA": "lao", "MM": "burma", "VN": "viet nam", "KR": "republic of korea", "IR": "islamic republic of iran", "SY": "syrian arab republic",
}


def name(code):
    """The English short name of an ISO code ("ru" or "RU" -> "Russia"), or "" when the code is not one."""
    return NAMES.get(str(code or "").strip().upper(), "")


def code_of(text):
    """The ISO code of a country written out in full ("Netherlands", "Россия"), or "" when the text is not exactly one country."""
    t = str(text or "").strip().lower()
    if not t: return ""
    for c, n in NAMES.items():
        if t == n.lower(): return c
    for c, alts in OTHER_NAMES.items():
        if t in alts.split("|"): return c
    return ""
