"""
Shared constants for the bot.
Contains country maps, phone prefix maps, and ZORO country mappings.
Centralized here to avoid duplication across bot.py and other modules.
"""

# --- MASTER COUNTRY MAPPER (250+ COUNTRIES & TERRITORIES) ---
ISO_COUNTRY_MAP = {
    "AF": "Afghanistan 🇦🇫", "AX": "Åland Islands 🇦🇽", "AL": "Albania 🇦🇱", "DZ": "Algeria 🇩🇿",
    "AS": "American Samoa 🇦🇸", "AD": "Andorra 🇦🇩", "AO": "Angola 🇦🇴", "AI": "Anguilla 🇦🇮",
    "AQ": "Antarctica 🇦🇶", "AG": "Antigua & Barbuda 🇦🇬", "AR": "Argentina 🇦🇷", "AM": "Armenia 🇦🇲",
    "AW": "Aruba 🇦🇼", "AU": "Australia 🇦🇺", "AT": "Austria 🇦🇹", "AZ": "Azerbaijan 🇦🇿",
    "BS": "Bahamas 🇧🇸", "BH": "Bahrain 🇧🇭", "BD": "Bangladesh 🇧🇩", "BB": "Barbados 🇧🇧",
    "BY": "Belarus 🇧🇾", "BE": "Belgium 🇧🇪", "BZ": "Belize 🇧🇿", "BJ": "Benin 🇧🇯",
    "BM": "Bermuda 🇧🇲", "BT": "Bhutan 🇧🇹", "BO": "Bolivia 🇧🇴", "BQ": "Caribbean Netherlands 🇧🇶",
    "BA": "Bosnia & Herzegovina 🇧🇦", "BW": "Botswana 🇧🇼", "BV": "Bouvet Island 🇧🇻", "BR": "Brazil 🇧🇷",
    "IO": "British Indian Ocean Territory 🇮🇴", "VG": "British Virgin Islands 🇻🇬", "BN": "Brunei 🇧🇳",
    "BG": "Bulgaria 🇧🇬", "BF": "Burkina Faso 🇧🇫", "BI": "Burundi 🇧🇮", "CV": "Cabo Verde 🇨🇻",
    "KH": "Cambodia 🇰🇭", "CM": "Cameroon 🇨🇲", "CA": "Canada 🇨🇦", "KY": "Cayman Islands 🇰🇾",
    "CF": "Central African Republic 🇨🇫", "TD": "Chad 🇹🇩", "CL": "Chile 🇨🇱", "CN": "China 🇨🇳",
    "CX": "Christmas Island 🇨🇽", "CC": "Cocos (Keeling) Islands 🇨🇨", "CO": "Colombia 🇨🇴",
    "KM": "Comoros 🇰🇲", "CD": "Congo (DRC) 🇨🇩", "CG": "Congo (Republic) 🇨🇬", "CK": "Cook Islands 🇨🇰",
    "CR": "Costa Rica 🇨🇷", "HR": "Croatia 🇭🇷", "CU": "Cuba 🇨🇺", "CW": "Curaçao 🇨🇼",
    "CY": "Cyprus 🇨🇾", "CZ": "Czechia 🇨🇿", "CI": "Côte d'Ivoire 🇨🇮", "DK": "Denmark 🇩🇰",
    "DJ": "Djibouti 🇩🇯", "DM": "Dominica 🇩🇲", "DO": "Dominican Republic 🇩🇴", "EC": "Ecuador 🇪🇨",
    "EG": "Egypt 🇪🇬", "SV": "El Salvador 🇸🇻", "GQ": "Equatorial Guinea 🇬🇶", "ER": "Eritrea 🇪🇷",
    "EE": "Estonia 🇪🇪", "SZ": "Eswatini 🇸🇿", "ET": "Ethiopia 🇪🇹", "FK": "Falkland Islands 🇫🇰",
    "FO": "Faroe Islands 🇫🇴", "FJ": "Fiji 🇫🇯", "FI": "Finland 🇫🇮", "FR": "France 🇫🇷",
    "GF": "French Guiana 🇬🇫", "PF": "French Polynesia 🇵🇫", "TF": "French Southern Territories 🇹🇫",
    "GA": "Gabon 🇬🇦", "GM": "Gambia 🇬🇲", "GE": "Georgia 🇬🇪", "DE": "Germany 🇩🇪",
    "GH": "Ghana 🇬🇭", "GI": "Gibraltar 🇬🇮", "GR": "Greece 🇬🇷", "GL": "Greenland 🇬🇱",
    "GD": "Grenada 🇬🇩", "GP": "Guadeloupe 🇬🇵", "GU": "Guam 🇬🇺", "GT": "Guatemala 🇬🇹",
    "GG": "Guernsey 🇬🇬", "GN": "Guinea 🇬🇳", "GW": "Guinea-Bissau 🇬🇼", "GY": "Guyana 🇬🇾",
    "HT": "Haiti 🇭🇹", "HM": "Heard & McDonald Islands 🇭🇲", "VA": "Vatican City 🇻🇦",
    "HN": "Honduras 🇭🇳", "HK": "Hong Kong 🇭🇰", "HU": "Hungary 🇭🇺", "IS": "Iceland 🇮🇸",
    "IN": "India 🇮🇳", "ID": "Indonesia 🇮🇩", "IR": "Iran 🇮🇷", "IQ": "Iraq 🇮🇶",
    "IE": "Ireland 🇮🇪", "IM": "Isle of Man 🇮🇲", "IL": "Israel 🇮🇱", "IT": "Italy 🇮🇹",
    "JM": "Jamaica 🇯🇲", "JP": "Japan 🇯🇵", "JE": "Jersey 🇯🇪", "JO": "Jordan 🇯🇴",
    "KZ": "Kazakhstan 🇰🇿", "KE": "Kenya 🇰🇪", "KI": "Kiribati 🇰🇮", "KP": "North Korea 🇰🇵",
    "KR": "South Korea 🇰🇷", "KW": "Kuwait 🇰🇼", "KG": "Kyrgyzstan 🇰🇬", "LA": "Laos 🇱🇦",
    "LV": "Latvia 🇱🇻", "LB": "Lebanon 🇱🇧", "LS": "Lesotho 🇱🇸", "LR": "Liberia 🇱🇷",
    "LY": "Libya 🇱🇾", "LI": "Liechtenstein 🇱🇮", "LT": "Lithuania 🇱🇹", "LU": "Luxembourg 🇱🇺",
    "MO": "Macau 🇲🇴", "MG": "Madagascar 🇲🇬", "MW": "Malawi 🇲🇼", "MY": "Malaysia 🇲🇾",
    "MV": "Maldives 🇲🇻", "ML": "Mali 🇲🇱", "MT": "Malta 🇲🇹", "MH": "Marshall Islands 🇲🇭",
    "MQ": "Martinique 🇲🇶", "MR": "Mauritania 🇲🇷", "MU": "Mauritius 🇲🇺", "YT": "Mayotte 🇾🇹",
    "MX": "Mexico 🇲🇽", "FM": "Micronesia 🇫🇲", "MD": "Moldova 🇲🇩", "MC": "Monaco 🇲🇨",
    "MN": "Mongolia 🇲🇳", "ME": "Montenegro 🇲🇪", "MS": "Montserrat 🇲🇸", "MA": "Morocco 🇲🇦",
    "MZ": "Mozambique 🇲🇿", "MM": "Myanmar 🇲🇲", "NA": "Namibia 🇳🇦", "NR": "Nauru 🇳🇷",
    "NP": "Nepal 🇳🇵", "NL": "Netherlands 🇳🇱", "NC": "New Caledonia 🇳🇨", "NZ": "New Zealand 🇳🇿",
    "NI": "Nicaragua 🇳🇮", "NE": "Niger 🇳🇪", "NG": "Nigeria 🇳🇬", "NU": "Niue 🇳🇺",
    "NF": "Norfolk Island 🇳🇫", "MK": "North Macedonia 🇲🇰", "MP": "Northern Mariana Islands 🇲🇵",
    "NO": "Norway 🇳🇴", "OM": "Oman 🇴🇲", "PK": "Pakistan 🇵🇰", "PW": "Palau 🇵🇼",
    "PS": "Palestine 🇵🇸", "PA": "Panama 🇵🇦", "PG": "Papua New Guinea 🇵🇬", "PY": "Paraguay 🇵🇾",
    "PE": "Peru 🇵🇪", "PH": "Philippines 🇵🇭", "PN": "Pitcairn Islands 🇵🇳", "PL": "Poland 🇵🇱",
    "PT": "Portugal 🇵🇹", "PR": "Puerto Rico 🇵🇷", "QA": "Qatar 🇶🇦", "RE": "Réunion 🇷🇪",
    "RO": "Romania 🇷🇴", "RU": "Russia 🇷🇺", "RW": "Rwanda 🇷🇼", "BL": "St. Barthélemy 🇧🇱",
    "SH": "St. Helena 🇸🇭", "KN": "St. Kitts & Nevis 🇰🇳", "LC": "St. Lucia 🇱🇨", "MF": "St. Martin 🇲🇫",
    "PM": "St. Pierre & Miquelon 🇵🇲", "VC": "St. Vincent & Grenadines 🇻🇨", "WS": "Samoa 🇼🇸",
    "SM": "San Marino 🇸🇲", "ST": "Sao Tome & Principe 🇸🇹", "SA": "Saudi Arabia 🇸🇦",
    "SN": "Senegal 🇸🇳", "RS": "Serbia 🇷🇸", "SC": "Seychelles 🇸🇨", "SL": "Sierra Leone 🇸🇱",
    "SG": "Singapore 🇸🇬", "SX": "Sint Maarten 🇸🇽", "SK": "Slovakia 🇸🇰", "SI": "Slovenia 🇸🇮",
    "SB": "Solomon Islands 🇸🇧", "SO": "Somalia 🇸🇴", "ZA": "South Africa 🇿🇦", "GS": "South Georgia 🇬🇸",
    "SS": "South Sudan 🇸🇸", "ES": "Spain 🇪🇸", "LK": "Sri Lanka 🇱🇰", "SD": "Sudan 🇸🇩",
    "SR": "Suriname 🇸🇷", "SJ": "Svalbard & Jan Mayen 🇸🇯", "SE": "Sweden 🇸🇪", "CH": "Switzerland 🇨🇭",
    "SY": "Syria 🇸🇾", "TW": "Taiwan 🇹🇼", "TJ": "Tajikistan 🇹🇯", "TZ": "Tanzania 🇹🇿",
    "TH": "Thailand 🇹🇭", "TL": "Timor-Leste 🇹🇱", "TG": "Togo 🇹🇬", "TK": "Tokelau 🇹🇰",
    "TO": "Tonga 🇹🇴", "TT": "Trinidad & Tobago 🇹🇹", "TN": "Tunisia 🇹🇳", "TR": "Türkiye 🇹🇷",
    "TM": "Turkmenistan 🇹🇲", "TC": "Turks & Caicos Islands 🇹🇨", "TV": "Tuvalu 🇹🇻",
    "UG": "Uganda 🇺🇬", "UA": "Ukraine 🇺🇦", "AE": "UAE 🇦🇪", "GB": "UK 🇬🇧",
    "US": "USA 🇺🇸", "UM": "U.S. Outlying Islands 🇺🇲", "UY": "Uruguay 🇺🇾", "UZ": "Uzbekistan 🇺🇿",
    "VU": "Vanuatu 🇻🇺", "VE": "Venezuela 🇻🇪", "VN": "Vietnam 🇻🇳", "VI": "U.S. Virgin Islands 🇻🇮",
    "WF": "Wallis & Futuna 🇼🇫", "EH": "Western Sahara 🇪🇭", "YE": "Yemen 🇾🇪", "ZM": "Zambia 🇿🇲",
    "ZW": "Zimbabwe 🇿🇼"
}

# --- MASTER PREFIX MAPPER (250+ PHONE CODES FOR SEARCH) ---
ISO_TO_PREFIX = {
    "AF": "93", "AX": "358", "AL": "355", "DZ": "213", "AS": "1684", "AD": "376", "AO": "244",
    "AI": "1264", "AQ": "672", "AG": "1268", "AR": "54", "AM": "374", "AW": "297", "AU": "61",
    "AT": "43", "AZ": "994", "BS": "1242", "BH": "973", "BD": "880", "BB": "1246", "BY": "375",
    "BE": "32", "BZ": "501", "BJ": "229", "BM": "1441", "BT": "975", "BO": "591", "BQ": "599",
    "BA": "387", "BW": "267", "BV": "47", "BR": "55", "IO": "246", "VG": "1284", "BN": "673",
    "BG": "359", "BF": "226", "BI": "257", "CV": "238", "KH": "855", "CM": "237", "CA": "1",
    "KY": "1345", "CF": "236", "TD": "235", "CL": "56", "CN": "86", "CX": "61", "CC": "61",
    "CO": "57", "KM": "269", "CD": "243", "CG": "242", "CK": "682", "CR": "506", "HR": "385",
    "CU": "53", "CW": "599", "CY": "357", "CZ": "420", "CI": "225", "DK": "45", "DJ": "253",
    "DM": "1767", "DO": "1809", "EC": "593", "EG": "20", "SV": "503", "GQ": "240", "ER": "291",
    "EE": "372", "SZ": "268", "ET": "251", "FK": "500", "FO": "298", "FJ": "679", "FI": "358",
    "FR": "33", "GF": "594", "PF": "689", "TF": "262", "GA": "241", "GM": "220", "GE": "995",
    "DE": "49", "GH": "233", "GI": "350", "GR": "30", "GL": "299", "GD": "1473", "GP": "590",
    "GU": "1671", "GT": "502", "GG": "44", "GN": "224", "GW": "245", "GY": "592", "HT": "509",
    "HM": "672", "VA": "379", "HN": "504", "HK": "852", "HU": "36", "IS": "354", "IN": "91",
    "ID": "62", "IR": "98", "IQ": "964", "IE": "353", "IM": "44", "IL": "972", "IT": "39",
    "JM": "1876", "JP": "81", "JE": "44", "JO": "962", "KZ": "7", "KE": "254", "KI": "686",
    "KP": "850", "KR": "82", "KW": "965", "KG": "996", "LA": "856", "LV": "371", "LB": "961",
    "LS": "266", "LR": "231", "LY": "218", "LI": "423", "LT": "370", "LU": "352", "MO": "853",
    "MG": "261", "MW": "265", "MY": "60", "MV": "960", "ML": "223", "MT": "356", "MH": "692",
    "MQ": "596", "MR": "222", "MU": "230", "YT": "262", "MX": "52", "FM": "691", "MD": "373",
    "MC": "377", "MN": "976", "ME": "382", "MS": "1664", "MA": "212", "MZ": "258", "MM": "95",
    "NA": "264", "NR": "674", "NP": "977", "NL": "31", "NC": "687", "NZ": "64", "NI": "505",
    "NE": "227", "NG": "234", "NU": "683", "NF": "672", "MK": "389", "MP": "1670", "NO": "47",
    "OM": "968", "PK": "92", "PW": "680", "PS": "970", "PA": "507", "PG": "675", "PY": "595",
    "PE": "51", "PH": "63", "PN": "870", "PL": "48", "PT": "351", "PR": "1787", "QA": "974",
    "RE": "262", "RO": "40", "RU": "7", "RW": "250", "BL": "590", "SH": "290", "KN": "1869",
    "LC": "1758", "MF": "590", "PM": "508", "VC": "1784", "WS": "685", "SM": "378", "ST": "239",
    "SA": "966", "SN": "221", "RS": "381", "SC": "248", "SL": "232", "SG": "65", "SX": "1721",
    "SK": "421", "SI": "386", "SB": "677", "SO": "252", "ZA": "27", "GS": "500", "SS": "211",
    "ES": "34", "LK": "94", "SD": "249", "SR": "597", "SJ": "47", "SE": "46", "CH": "41",
    "SY": "963", "TW": "886", "TJ": "992", "TZ": "255", "TH": "66", "TL": "670", "TG": "228",
    "TK": "690", "TO": "676", "TT": "1868", "TN": "216", "TR": "90", "TM": "993", "TC": "1649",
    "TV": "688", "UG": "256", "UA": "380", "AE": "971", "GB": "44", "US": "1", "UM": "1",
    "UY": "598", "UZ": "998", "VU": "678", "VE": "58", "VN": "84", "VI": "1340", "WF": "681",
    "EH": "212", "YE": "967", "ZM": "260", "ZW": "263"
}

# --- ZORO ISO-3166 Alpha-3 → Alpha-2 + Name ---
ZORO_COUNTRY_MAP = {
    "ABW": ("AW", "Aruba"), "AFG": ("AF", "Afghanistan"), "AGO": ("AO", "Angola"),
    "ALB": ("AL", "Albania"), "AND": ("AD", "Andorra"), "ARE": ("AE", "UAE"),
    "ARG": ("AR", "Argentina"), "ARM": ("AM", "Armenia"), "ATG": ("AG", "Antigua & Barbuda"),
    "AUS": ("AU", "Australia"), "AUT": ("AT", "Austria"), "AZE": ("AZ", "Azerbaijan"),
    "BDI": ("BI", "Burundi"), "BEL": ("BE", "Belgium"), "BEN": ("BJ", "Benin"),
    "BFA": ("BF", "Burkina Faso"), "BGD": ("BD", "Bangladesh"), "BGR": ("BG", "Bulgaria"),
    "BHR": ("BH", "Bahrain"), "BHS": ("BS", "Bahamas"), "BIH": ("BA", "Bosnia"),
    "BLR": ("BY", "Belarus"), "BLZ": ("BZ", "Belize"), "BOL": ("BO", "Bolivia"),
    "BRA": ("BR", "Brazil"), "BRB": ("BB", "Barbados"), "BRN": ("BN", "Brunei"),
    "BTN": ("BT", "Bhutan"), "BWA": ("BW", "Botswana"), "CAF": ("CF", "Central African Rep."),
    "CAN": ("CA", "Canada"), "CHE": ("CH", "Switzerland"), "CHL": ("CL", "Chile"),
    "CIV": ("CI", "Ivory Coast"), "CMR": ("CM", "Cameroon"), "COD": ("CD", "DR Congo"),
    "COG": ("CG", "Congo"), "COL": ("CO", "Colombia"), "COM": ("KM", "Comoros"),
    "CPV": ("CV", "Cape Verde"), "CRI": ("CR", "Costa Rica"), "CUB": ("CU", "Cuba"),
    "CYP": ("CY", "Cyprus"), "CZE": ("CZ", "Czech Republic"), "DEU": ("DE", "Germany"),
    "DJI": ("DJ", "Djibouti"), "DMA": ("DM", "Dominica"), "DNK": ("DK", "Denmark"),
    "DOM": ("DO", "Dominican Rep."), "DZA": ("DZ", "Algeria"), "ECU": ("EC", "Ecuador"),
    "EGY": ("EG", "Egypt"), "ERI": ("ER", "Eritrea"), "ESP": ("ES", "Spain"),
    "EST": ("EE", "Estonia"), "ETH": ("ET", "Ethiopia"), "FIN": ("FI", "Finland"),
    "FJI": ("FJ", "Fiji"), "FRA": ("FR", "France"), "FSM": ("FM", "Micronesia"),
    "GAB": ("GA", "Gabon"), "GBR": ("GB", "United Kingdom"), "GEO": ("GE", "Georgia"),
    "GHA": ("GH", "Ghana"), "GIB": ("GI", "Gibraltar"), "GIN": ("GN", "Guinea"),
    "GLP": ("GP", "Guadeloupe"), "GMB": ("GM", "Gambia"), "GNB": ("GW", "Guinea-Bissau"),
    "GNQ": ("GQ", "Equatorial Guinea"), "GRC": ("GR", "Greece"), "GRD": ("GD", "Grenada"),
    "GTM": ("GT", "Guatemala"), "GUF": ("GF", "French Guiana"), "GUM": ("GU", "Guam"),
    "GUY": ("GY", "Guyana"), "HKG": ("HK", "Hong Kong"), "HND": ("HN", "Honduras"),
    "HRV": ("HR", "Croatia"), "HTI": ("HT", "Haiti"), "HUN": ("HU", "Hungary"),
    "IDN": ("ID", "Indonesia"), "IMN": ("IM", "Isle of Man"), "IND": ("IN", "India"),
    "IRL": ("IE", "Ireland"), "IRN": ("IR", "Iran"), "IRQ": ("IQ", "Iraq"),
    "ISL": ("IS", "Iceland"), "ISR": ("IL", "Israel"), "ITA": ("IT", "Italy"),
    "JAM": ("JM", "Jamaica"), "JOR": ("JO", "Jordan"), "JPN": ("JP", "Japan"),
    "KAZ": ("KZ", "Kazakhstan"), "KEN": ("KE", "Kenya"), "KGZ": ("KG", "Kyrgyzstan"),
    "KHM": ("KH", "Cambodia"), "KIR": ("KI", "Kiribati"), "KNA": ("KN", "Saint Kitts"),
    "KOR": ("KR", "South Korea"), "KWT": ("KW", "Kuwait"), "LAO": ("LA", "Laos"),
    "LBN": ("LB", "Lebanon"), "LBR": ("LR", "Liberia"), "LBY": ("LY", "Libya"),
    "LCA": ("LC", "Saint Lucia"), "LIE": ("LI", "Liechtenstein"), "LKA": ("LK", "Sri Lanka"),
    "LSO": ("LS", "Lesotho"), "LTU": ("LT", "Lithuania"), "LUX": ("LU", "Luxembourg"),
    "LVA": ("LV", "Latvia"), "MAC": ("MO", "Macau"), "MAR": ("MA", "Morocco"),
    "MCO": ("MC", "Monaco"), "MDA": ("MD", "Moldova"), "MDG": ("MG", "Madagascar"),
    "MDV": ("MV", "Maldives"), "MEX": ("MX", "Mexico"), "MHL": ("MH", "Marshall Islands"),
    "MKD": ("MK", "North Macedonia"), "MLI": ("ML", "Mali"), "MLT": ("MT", "Malta"),
    "MMR": ("MM", "Myanmar"), "MNE": ("ME", "Montenegro"), "MNG": ("MN", "Mongolia"),
    "MNP": ("MP", "N. Mariana Isl."), "MOZ": ("MZ", "Mozambique"), "MRT": ("MR", "Mauritania"),
    "MTQ": ("MQ", "Martinique"), "MUS": ("MU", "Mauritius"), "MWI": ("MW", "Malawi"),
    "MYS": ("MY", "Malaysia"), "NAM": ("NA", "Namibia"), "NER": ("NE", "Niger"),
    "NGA": ("NG", "Nigeria"), "NIC": ("NI", "Nicaragua"), "NLD": ("NL", "Netherlands"),
    "NOR": ("NO", "Norway"), "NPL": ("NP", "Nepal"), "NRU": ("NR", "Nauru"),
    "NZL": ("NZ", "New Zealand"), "OMN": ("OM", "Oman"), "PAK": ("PK", "Pakistan"),
    "PAN": ("PA", "Panama"), "PER": ("PE", "Peru"), "PHL": ("PH", "Philippines"),
    "PLW": ("PW", "Palau"), "PNG": ("PG", "Papua New Guinea"), "POL": ("PL", "Poland"),
    "PRI": ("PR", "Puerto Rico"), "PRK": ("KP", "North Korea"), "PRT": ("PT", "Portugal"),
    "PRY": ("PY", "Paraguay"), "PSE": ("PS", "Palestine"), "QAT": ("QA", "Qatar"),
    "REU": ("RE", "Reunion"), "ROU": ("RO", "Romania"), "RUS": ("RU", "Russia"),
    "RWA": ("RW", "Rwanda"), "SAU": ("SA", "Saudi Arabia"), "SDN": ("SD", "Sudan"),
    "SEN": ("SN", "Senegal"), "SGP": ("SG", "Singapore"), "SLB": ("SB", "Solomon Islands"),
    "SLE": ("SL", "Sierra Leone"), "SLV": ("SV", "El Salvador"), "SMR": ("SM", "San Marino"),
    "SOM": ("SO", "Somalia"), "SRB": ("RS", "Serbia"), "SSD": ("SS", "South Sudan"),
    "STP": ("ST", "Sao Tome"), "SUR": ("SR", "Suriname"), "SVK": ("SK", "Slovakia"),
    "SVN": ("SI", "Slovenia"), "SWE": ("SE", "Sweden"), "SWZ": ("SZ", "Eswatini"),
    "SYC": ("SC", "Seychelles"), "SYR": ("SY", "Syria"), "TCD": ("TD", "Chad"),
    "TGO": ("TG", "Togo"), "THA": ("TH", "Thailand"), "TJK": ("TJ", "Tajikistan"),
    "TKM": ("TM", "Turkmenistan"), "TLS": ("TL", "Timor-Leste"), "TON": ("TO", "Tonga"),
    "TTO": ("TT", "Trinidad & Tobago"), "TUN": ("TN", "Tunisia"), "TUR": ("TR", "Turkey"),
    "TUV": ("TV", "Tuvalu"), "TWN": ("TW", "Taiwan"), "TZA": ("TZ", "Tanzania"),
    "UGA": ("UG", "Uganda"), "UKR": ("UA", "Ukraine"), "URY": ("UY", "Uruguay"),
    "USA": ("US", "USA"), "UZB": ("UZ", "Uzbekistan"), "VAT": ("VA", "Vatican City"),
    "VCT": ("VC", "St. Vincent & Grenadines"), "VEN": ("VE", "Venezuela"), "VNM": ("VN", "Vietnam"),
    "VUT": ("VU", "Vanuatu"), "WSM": ("WS", "Samoa"), "XKX": ("XK", "Kosovo"),
    "YEM": ("YE", "Yemen"), "ZAF": ("ZA", "South Africa"), "ZMB": ("ZM", "Zambia"),
    "ZWE": ("ZW", "Zimbabwe")
}


def flag_emoji(alpha2: str, html: bool = False) -> str:
    """Generate flag emoji from ISO Alpha-2 country code (optionally as custom tg-emoji HTML)."""
    try:
        a2 = alpha2.upper()
        unicode_flag = "".join(chr(0x1F1E6 + ord(c) - ord('A')) for c in a2)
        if html and a2 in FLAG_CUSTOM_EMOJIS:
            return f'<tg-emoji emoji-id="{FLAG_CUSTOM_EMOJIS[a2]}">{unicode_flag}</tg-emoji>'
        return unicode_flag
    except Exception:
        return "🏳️"


# --- TELEGRAM CUSTOM / PREMIUM FLAG EMOJI IDS (200 FLAGS) ---
FLAG_CUSTOM_EMOJIS = {
    "DEFAULT": "5294236848103643477",  # 🚩
    "AF": "5291937511591925566",       # 🇦🇫 Afghanistan
    "AX": "5294077418917616055",       # 🇦🇽 Aland Islands
    "AL": "5294202819077756005",       # 🇦🇱 Albania
    "DZ": "5294048127240655242",       # 🇩🇿 Algeria
    "AS": "5291994273879709721",       # 🇦🇸 American Samoa
    "AD": "5294215205763434181",       # 🇦🇩 Andorra
    "AO": "5294516785482062829",       # 🇦🇴 Angola
    "AI": "5292186323342350940",       # 🇦🇮 Anguilla
    "AG": "5294005972136647964",       # 🇦🇬 Antigua & Barbuda
    "AR": "5292208210495689627",       # 🇦🇷 Argentina
    "AM": "5291978717508164018",       # 🇦🇲 Armenia
    "AW": "5294007002928798927",       # 🇦🇼 Aruba
    "AU": "5294444247779399477",       # 🇦🇺 Australia
    "AT": "5291975174160145850",       # 🇦🇹 Austria
    "AZ": "5294323533428579078",       # 🇦🇿 Azerbaijan
    "BS": "5294031587321600012",       # 🇧🇸 Bahamas
    "BH": "5294108398516720753",       # 🇧🇭 Bahrain
    "BD": "5291824687096027834",       # 🇧🇩 Bangladesh
    "BB": "5294526187165471742",       # 🇧🇧 Barbados
    "BY": "5294134426018536120",       # 🇧🇾 Belarus
    "BE": "5291774466043435275",       # 🇧🇪 Belgium
    "BZ": "5294171848068584842",       # 🇧🇿 Belize
    "BJ": "5293984969746566866",       # 🇧🇯 Benin
    "BT": "5294121983498277263",       # 🇧🇹 Bhutan
    "BO": "5294201479047957700",       # 🇧🇴 Bolivia
    "BW": "5294026179957772585",       # 🇧🇼 Botswana
    "BR": "5291892229751723900",       # 🇧🇷 Brazil
    "BN": "5292098293692650297",       # 🇧🇳 Brunei
    "BG": "5294308947719640437",       # 🇧🇬 Bulgaria
    "BF": "5294153164960848949",       # 🇧🇫 Burkina Faso
    "BI": "5294051631933967760",       # 🇧🇮 Burundi
    "KH": "5294225191562400452",       # 🇰🇭 Cambodia
    "CM": "5291997306126626950",       # 🇨🇲 Cameroon
    "CA": "5292290347450259214",       # 🇨🇦 Canada
    "CV": "5292203503211535593",       # 🇨🇻 Cape Verde
    "CF": "5294210571493724819",       # 🇨🇫 Central African Rep.
    "TD": "5291780728105753403",       # 🇹🇩 Chad
    "CL": "5294231037012888049",       # 🇨🇱 Chile
    "CN": "5294068833277990704",       # 🇨🇳 China
    "CO": "5294010206974397371",       # 🇨🇴 Colombia
    "KM": "5294351381996521508",       # 🇰🇲 Comoros
    "CG": "5294035229453865597",       # 🇨🇬 Congo
    "CD": "5294035229453865597",       # 🇨🇩 DR Congo
    "CK": "5292098684534675100",       # 🇨🇰 Cook Islands
    "CR": "5292063805105263554",       # 🇨🇷 Costa Rica
    "CI": "5293991322003200135",       # 🇨🇮 Ivory Coast / Cote d'Ivoire
    "HR": "5291999676948569127",       # 🇭🇷 Croatia
    "CU": "5291963947115631526",       # 🇨🇺 Cuba
    "CY": "5294062721539526918",       # 🇨🇾 Cyprus
    "CZ": "5294242852467923382",       # 🇨🇿 Czech Republic
    "DK": "5294531860817268837",       # 🇩🇰 Denmark
    "DJ": "5294127214768468283",       # 🇩🇯 Djibouti
    "DM": "5294485513825178032",       # 🇩🇲 Dominica
    "DO": "5294522197140857947",       # 🇩🇴 Dominican Rep.
    "EC": "5292083733753517221",       # 🇪🇨 Ecuador
    "EG": "5293992082212409502",       # 🇪🇬 Egypt
    "SV": "5294337307388695687",       # 🇸🇻 El Salvador
    "ENG": "5294410107084365278",      # 🏴 England
    "GQ": "5292170045416297012",       # 🇬🇶 Equatorial Guinea
    "ER": "5291922054004625949",       # 🇪🇷 Eritrea
    "EE": "5291951143818123103",       # 🇪🇪 Estonia
    "ET": "5292245976143124155",       # 🇪🇹 Ethiopia
    "EU": "5291992809295861098",       # 🇪🇺 European Union
    "GI": "5292055799286224027",       # 🇬🇮 Gibraltar
    "GM": "5294399820637688352",       # 🇬🇲 Gambia
    "GL": "5292014752283774878",       # 🇬🇱 Greenland
    "FI": "5294049961191690629",       # 🇫🇮 Finland
    "FR": "5291817660529533837",       # 🇫🇷 France
    "GA": "5294321325815389139",       # 🇬🇦 Gabon
    "GE": "5294349389131697267",       # 🇬🇪 Georgia
    "DE": "5292013274815028523",       # 🇩🇪 Germany
    "GH": "5294347396266873249",       # 🇬🇭 Ghana
    "GR": "5291948395039054764",       # 🇬🇷 Greece
    "GW": "5294409819321550432",       # 🇬🇼 Guinea-Bissau
    "GT": "5294336633078831209",       # 🇬🇹 Guatemala
    "GN": "5291892096607739008",       # 🇬🇳 Guinea
    "GY": "5292062692708736193",       # 🇬🇾 Guyana
    "HT": "5292045130587462814",       # 🇭🇹 Haiti
    "HN": "5291901034434682297",       # 🇭🇳 Honduras
    "HK": "5292166459118606932",       # 🇭🇰 Hong Kong
    "HU": "5294229581018975260",       # 🇭🇺 Hungary
    "IS": "5294354358408859664",       # 🇮🇸 Iceland
    "IN": "5291933173674957761",       # 🇮🇳 India
    "ID": "5294378161117614233",       # 🇮🇩 Indonesia
    "IR": "5294220170745630736",       # 🇮🇷 Iran
    "IQ": "5294325010897327367",       # 🇮🇶 Iraq
    "IE": "5294471971793293647",       # 🇮🇪 Ireland
    "IM": "5294318478252070646",       # 🇮🇲 Isle of Man
    "IL": "5294069056616289553",       # 🇮🇱 Israel
    "IT": "5291826830284709120",       # 🇮🇹 Italy
    "JM": "5294505107465982830",       # 🇯🇲 Jamaica
    "JP": "5291799063321139445",       # 🇯🇵 Japan
    "JE": "5291950280529697493",       # 🇯🇪 Jersey
    "JO": "5291988613112814801",       # 🇯🇴 Jordan
    "KZ": "5294227175837290463",       # 🇰🇿 Kazakhstan
    "KE": "5292111852904416801",       # 🇰🇪 Kenya
    "KI": "5294538934628405146",       # 🇰🇮 Kiribati
    "KP": "5294193812531333564",       # 🇰🇵 North Korea
    "KR": "5294408281723262763",       # 🇰🇷 South Korea
    "KW": "5292066437920218075",       # 🇰🇼 Kuwait
    "KG": "5292091954320922577",       # 🇰🇬 Kyrgyzstan
    "LA": "5291981530711746037",       # 🇱🇦 Laos
    "LV": "5292236016113966127",       # 🇱🇻 Latvia
    "LB": "5294193108156699621",       # 🇱🇧 Lebanon
    "LS": "5292040693886247604",       # 🇱🇸 Lesotho
    "LR": "5291793810576137439",       # 🇱🇷 Liberia
    "LY": "5291858711826946840",       # 🇱🇾 Libya
    "LI": "5292048742654957785",       # 🇱🇮 Liechtenstein
    "LT": "5294343084119708700",       # 🇱🇹 Lithuania
    "LU": "5294423709245787718",       # 🇱🇺 Luxembourg
    "MK": "5294023611567332075",       # 🇲🇰 North Macedonia
    "MG": "5291991568050312348",       # 🇲🇬 Madagascar
    "MW": "5294241881805312589",       # 🇲🇼 Malawi
    "MY": "5291858351049696702",       # 🇲🇾 Malaysia
    "MV": "5292004203844097218",       # 🇲🇻 Maldives
    "ML": "5292086972158858331",       # 🇲🇱 Mali
    "MT": "5294532213004588353",       # 🇲🇹 Malta
    "MH": "5294180730060954484",       # 🇲🇭 Marshall Islands
    "MR": "5294429743674840973",       # 🇲🇷 Mauritania
    "MU": "5294127824653797277",       # 🇲🇺 Mauritius
    "MX": "5294535073452809778",       # 🇲🇽 Mexico
    "FM": "5291838156113470124",       # 🇫🇲 Micronesia
    "MD": "5294158486425325375",       # 🇲🇩 Moldova
    "MC": "5294378161117614233",       # 🇲🇨 Monaco
    "MN": "5294316532631883496",       # 🇲🇳 Mongolia
    "MA": "5292108962391414885",       # 🇲🇦 Morocco
    "MZ": "5294086708931874940",       # 🇲🇿 Mozambique
    "MM": "5294254478944393569",       # 🇲🇲 Myanmar
    "NA": "5292021761670404922",       # 🇳🇦 Namibia
    "NR": "5294463274484521342",       # 🇳🇷 Nauru
    "NP": "5294458756178924088",       # 🇳🇵 Nepal
    "NL": "5291917797692042265",       # 🇳🇱 Netherlands
    "NZ": "5294189019347833274",       # 🇳🇿 New Zealand
    "NI": "5294240825243358100",       # 🇳🇮 Nicaragua
    "NE": "5291809418487290691",       # 🇳🇪 Niger
    "NG": "5294456308047563965",       # 🇳🇬 Nigeria
    "NU": "5294471336138134209",       # 🇳🇺 Niue
    "NO": "5291761718580502030",       # 🇳🇴 Norway
    "OM": "5291813666209946812",       # 🇴🇲 Oman
    "PK": "5291825606219029010",       # 🇵🇰 Pakistan
    "PS": "5294289826525238172",       # 🇵🇸 Palestine
    "PA": "5291959935616178405",       # 🇵🇦 Panama
    "PG": "5291917995260533077",       # 🇵🇬 Papua New Guinea
    "PY": "5294525611639852679",       # 🇵🇾 Paraguay
    "PH": "5291798075478661634",       # 🇵🇭 Philippines
    "PE": "5292099427564018941",       # 🇵🇪 Peru
    "PL": "5292190970496963836",       # 🇵🇱 Poland
    "PT": "5294436555492973610",       # 🇵🇹 Portugal
    "PR": "5292121516580820347",       # 🇵🇷 Puerto Rico
    "QA": "5292166360334357676",       # 🇶🇦 Qatar
    "RO": "5294107724206856227",       # 🇷🇴 Romania
    "RU": "5294335323113807278",       # 🇷🇺 Russia
    "RW": "5294191265615729158",       # 🇷🇼 Rwanda
    "SM": "5292147350809106831",       # 🇸🇲 San Marino
    "ST": "5292183188016222701",       # 🇸🇹 Sao Tome & Principe
    "SA": "5294163983983463099",       # 🇸🇦 Saudi Arabia
    "SCT": "5294434665707368018",      # 🏴 Scotland
    "SN": "5292087023698466689",       # 🇸🇳 Senegal
    "RS": "5294458584380230360",       # 🇷🇸 Serbia
    "SC": "5291891186074672309",       # 🇸🇨 Seychelles
    "SL": "5294494314213167952",       # 🇸🇱 Sierra Leone
    "SG": "5294451304410663668",       # 🇸🇬 Singapore
    "SK": "5294538440707166931",       # 🇸🇰 Slovakia
    "SI": "5294279359689938006",       # 🇸🇮 Slovenia
    "SB": "5294283890880433237",       # 🇸🇧 Solomon Islands
    "SO": "5294058817414255960",       # 🇸🇴 Somalia
    "ZA": "5294325281480266304",       # 🇿🇦 South Africa
    "ES": "5294513087515216901",       # 🇪🇸 Spain
    "LK": "5292102670264328257",       # 🇱🇰 Sri Lanka
    "SD": "5294177148058228060",       # 🇸🇩 Sudan
    "SR": "5294396668131692138",       # 🇸🇷 Suriname
    "SZ": "5294312482477724867",       # 🇸🇿 Eswatini
    "SE": "5291737091238026321",       # 🇸🇪 Sweden
    "CH": "5291791748991835084",       # 🇨🇭 Switzerland
    "SY": "5294013428199869487",       # 🇸🇾 Syria
    "TW": "5294095745543069603",       # 🇹🇼 Taiwan
    "TJ": "5294120269806328883",       # 🇹🇯 Tajikistan
    "TZ": "5292146096678658977",       # 🇹🇿 Tanzania
    "TH": "5293994384314882755",       # 🇹🇭 Thailand
    "TG": "5294097669688415562",       # 🇹🇬 Togo
    "TO": "5294283689016973348",       # 🇹🇴 Tonga
    "TT": "5294362935458548705",       # 🇹🇹 Trinidad & Tobago
    "TN": "5294484680601521871",       # 🇹🇳 Tunisia
    "TR": "5293993400767367408",       # 🇹🇷 Turkey
    "TM": "5294098958178603764",       # 🇹🇲 Turkmenistan
    "TC": "5294320866253884749",       # 🇹🇨 Turks & Caicos
    "US": "5294244076533600593",       # 🇺🇸 USA
    "UG": "5294192317882716626",       # 🇺🇬 Uganda
    "AE": "5294314831824835370",       # 🇦🇪 UAE
    "GB": "5293993521026453119",       # 🇬🇧 United Kingdom
    "UA": "5294263837678131580",       # 🇺🇦 Ukraine
    "VU": "5294448585696368047",       # 🇻🇺 Vanuatu
    "UZ": "5294217645304864345",       # 🇺🇿 Uzbekistan
    "UY": "5291928449210932974",       # 🇺🇾 Uruguay
    "VE": "5294476442854247878",       # 🇻🇪 Venezuela
    "VN": "5294235963340379688",       # 🇻🇳 Vietnam
    "VI": "5294228039125718124",       # 🇻🇮 Virgin Islands
    "WLS": "5294139949346476093",      # 🏴 Wales
    "YE": "5294058972033076492",       # 🇾🇪 Yemen
    "ZM": "5294100109229838880",       # 🇿🇲 Zambia
    "ZW": "5294422158762592930",       # 🇿🇼 Zimbabwe
}

# Country name/alias to Alpha-2 code mapper for custom emoji lookup
COUNTRY_NAME_TO_CODE = {
    "india": "IN", "usa": "US", "united states": "US", "russia": "RU",
    "indonesia": "ID", "brazil": "BR", "vietnam": "VN", "philippines": "PH",
    "thailand": "TH", "malaysia": "MY", "pakistan": "PK", "bangladesh": "BD",
    "nigeria": "NG", "ukraine": "UA", "kazakhstan": "KZ", "turkey": "TR", "türkiye": "TR",
    "egypt": "EG", "south africa": "ZA", "mexico": "MX", "colombia": "CO",
    "argentina": "AR", "china": "CN", "japan": "JP", "korea": "KR", "south korea": "KR",
    "north korea": "KP", "germany": "DE", "france": "FR", "uk": "GB", "united kingdom": "GB",
    "italy": "IT", "spain": "ES", "poland": "PL", "canada": "CA", "australia": "AU",
    "afghanistan": "AF", "albania": "AL", "algeria": "DZ", "andorra": "AD", "angola": "AO",
    "anguilla": "AI", "armenia": "AM", "aruba": "AW", "austria": "AT", "azerbaijan": "AZ",
    "bahamas": "BS", "bahrain": "BH", "barbados": "BB", "belarus": "BY", "belgium": "BE",
    "belize": "BZ", "benin": "BJ", "bhutan": "BT", "bolivia": "BO", "botswana": "BW",
    "bulgaria": "BG", "burkina faso": "BF", "burundi": "BI", "cambodia": "KH", "cameroon": "CM",
    "cape verde": "CV", "chile": "CL", "costa rica": "CR", "croatia": "HR", "cuba": "CU",
    "cyprus": "CY", "czech republic": "CZ", "czechia": "CZ", "denmark": "DK", "djibouti": "DJ",
    "dominica": "DM", "dominican rep.": "DO", "dominican republic": "DO", "ecuador": "EC",
    "el salvador": "SV", "england": "ENG", "estonia": "EE", "ethiopia": "ET", "finland": "FI",
    "gambia": "GM", "georgia": "GE", "ghana": "GH", "gibraltar": "GI", "greece": "GR",
    "greenland": "GL", "guatemala": "GT", "guinea": "GN", "guyana": "GY", "haiti": "HT",
    "honduras": "HN", "hong kong": "HK", "hungary": "HU", "iceland": "IS", "iran": "IR",
    "iraq": "IQ", "ireland": "IE", "israel": "IL", "jamaica": "JM", "jordan": "JO",
    "kenya": "KE", "kuwait": "KW", "kyrgyzstan": "KG", "laos": "LA", "latvia": "LV",
    "lebanon": "LB", "liberia": "LR", "libya": "LY", "lithuania": "LT", "luxembourg": "LU",
    "madagascar": "MG", "malawi": "MW", "maldives": "MV", "mali": "ML", "malta": "MT",
    "mauritania": "MR", "mauritius": "MU", "moldova": "MD", "monaco": "MC", "mongolia": "MN",
    "morocco": "MA", "mozambique": "MZ", "myanmar": "MM", "namibia": "NA", "nepal": "NP",
    "netherlands": "NL", "new zealand": "NZ", "nicaragua": "NI", "niger": "NE", "norway": "NO",
    "oman": "OM", "palestine": "PS", "panama": "PA", "papua new guinea": "PG", "paraguay": "PY",
    "peru": "PE", "portugal": "PT", "puerto rico": "PR", "qatar": "QA", "romania": "RO",
    "rwanda": "RW", "saudi arabia": "SA", "scotland": "SCT", "senegal": "SN", "serbia": "RS",
    "seychelles": "SC", "sierra leone": "SL", "singapore": "SG", "slovakia": "SK", "slovenia": "SI",
    "somalia": "SO", "sri lanka": "LK", "sudan": "SD", "suriname": "SR", "sweden": "SE",
    "switzerland": "CH", "syria": "SY", "taiwan": "TW", "tajikistan": "TJ", "tanzania": "TZ",
    "togo": "TG", "tonga": "TO", "trinidad": "TT", "tunisia": "TN", "turkmenistan": "TM",
    "uganda": "UG", "uae": "AE", "uruguay": "UY", "uzbekistan": "UZ", "venezuela": "VE",
    "wales": "WLS", "yemen": "YE", "zambia": "ZM", "zimbabwe": "ZW"
}


def get_flag_custom_emoji_id(code_or_name: str) -> str | None:
    """Return custom emoji ID for country code or country name if found."""
    if not code_or_name:
        return None
    c_upper = code_or_name.upper().strip()
    if c_upper in FLAG_CUSTOM_EMOJIS:
        return FLAG_CUSTOM_EMOJIS[c_upper]
    
    c_lower = code_or_name.lower().strip()
    for name, code in COUNTRY_NAME_TO_CODE.items():
        if name in c_lower:
            return FLAG_CUSTOM_EMOJIS.get(code)
    return None


def get_cat_flag(cat_name: str, html: bool = True) -> str:
    """Find matching flag for category name, returning custom tg-emoji HTML or unicode flag."""
    name_lower = cat_name.lower()
    for name, code in COUNTRY_NAME_TO_CODE.items():
        if name in name_lower:
            return flag_emoji(code, html=html)
    return "🌍"


# Pre-computed sorted list for ZORO country browsing with custom emoji support
ZORO_ALL_COUNTRIES = [
    {
        "code": a2,
        "flag": flag_emoji(a2, html=False),
        "flag_html": flag_emoji(a2, html=True),
        "emoji_id": FLAG_CUSTOM_EMOJIS.get(a2.upper(), FLAG_CUSTOM_EMOJIS.get("DEFAULT", "5294236848103643477")),
        "name": name
    }
    for code, (a2, name) in sorted(ZORO_COUNTRY_MAP.items(), key=lambda kv: kv[1][1])
]

# Pagination constants
COUNTRIES_PER_PAGE = 10
ZORO_PER_PAGE = 10
COUNTRY_PER_PAGE = 20


# --- TELEGRAM CUSTOM / PREMIUM UI & NEWS EMOJIS (200 EMOJIS) ---
UI_CUSTOM_EMOJIS = {
    # QR Bot & Tech UI Icons
    '🏓': '5195033767969839232',
    '🐍': '6325849372256898767',
    '💾': '5445221832074483553',
    '💿': '5377505475015235101',
    '📀': '5377505475015235101',
    '🔋': '6325415120998502570',
    '🗂': '5445221832074483553',
    '🗂️': '5445221832074483553',
    '🗄': '5332455502917949981',
    '🗄️': '5332455502917949981',
    '🏎': '5195033767969839232',
    '🏎️': '5195033767969839232',
    '⚖': '5312441427764989435',
    '⚖️': '5312441427764989435',
    '🛡': '6325790127478018778',
    '🛡️': '6325790127478018778',
    '⚙': '6325849814638531007',
    '⚙️': '6325849814638531007',
    '⏱': '6206118633370818254',
    '⏱️': '6206118633370818254',
    '🖥': '6325332404223350181',
    '🖥️': '6325332404223350181',
    '🗑': '6205842887377165039',
    '🗑️': '6205842887377165039',
    '🏷': '6325655265504923619',
    '🏷️': '6325655265504923619',
    '🏠': '5332455502917949981',
    '🏦': '5332455502917949981',
    '✓': '6325382986053193737',
    '✕': '6325844463109280731',
    '✎': '5197269100878907942',
    '⬡': '6325717349257187998',
    '◉': '6307777408300753473',
    '▤': '6325667390197600621',
    '⊞': '6325849814638531007',
    '▸': '6325415120998502570',
    '◈': '6205965994528086727',
    '⊗': '6205842887377165039',

    # Money / Economy / Banking
    "💰": "6325444137797554944",       # Erangle Animated Money
    "money_bag": "6325444137797554944",
    "money_bag_finance": "5287231198098117669",
    "money_bag_2": "6205969928718129358",
    "money_bag_3": "6206196428113450490",
    "money_bag_4": "6206414917394765704",
    "money_bag_5": "6206457596484786411",
    "money_bag_6": "6205982457137731714",
    "money_bag_7": "6206313813864617518",
    "💵": "6325624346035359985",       # Erangle Animated Dollar Bill ($)
    "dollar": "6325624346035359985",
    "dollar_animated": "6325624346035359985",
    "💶": "5197369495739455200",
    "💷": "5377775044342599336",
    "💴": "5197161121106123533",
    "🪙": "5377505475015235101",       # Finance Gold Crypto Coin
    "crypto": "6325624346035359985",
    "💸": "6206405459876779229",
    "flying_money": "6206405459876779229",
    "flying_money_2": "6204110126274582365",
    "flying_money_3": "6206465984555914717",
    "flying_money_4": "6206321003639870472",
    "flying_money_5": "6206499923387488362",
    "flying_money_6": "6206034817084036949",
    "flying_money_7": "6205975911607572160",
    "💲": "6205983294656356400",
    "dollar_sign": "6205983294656356400",
    "dollar_sign_2": "6206471194351245524",
    "💳": "5445353829304387411",       # Finance Card
    "card": "5445353829304387411",
    "card_2": "6206233180148603109",
    "card_3": "6305298855688672996",
    "🏦": "5332455502917949981",       # Finance Bank
    "bank": "5332455502917949981",
    "bank_2": "6205988689135277308",
    "bank_3": "6206317537601264099",
    "👛": "6325416826100519483",       # Erangle Animated Purse
    "purse": "6325416826100519483",
    "💱": "5312441427764989435",       # Finance Exchange
    "exchange": "5312441427764989435",
    "💎": "6325717349257187998",       # Erangle Animated Diamond
    "diamond": "6325717349257187998",
    "diamond_2": "6325561656692708246",
    "diamond_3": "6325329444990881993",
    "diamond_4": "6325821111372092431",
    "👋": "6206254612035409256",
    "wave": "6206254612035409256",
    "🆔": "6325655265504923619",       # Erangle Animated ID Badge
    "id": "6325655265504923619",
    "🪪": "6325618702448332955",       # Erangle Animated ID Card
    "id_card": "6325618702448332955",
    "⚡": "6325415120998502570",       # Erangle Animated Lightning
    "zap": "6325415120998502570",
    "vip": "6325564362522104416",       # Erangle Animated Crown for VIP
    "👑": "6325564362522104416",       # Erangle Animated Crown
    "crown": "6325564362522104416",
    "🛒": "5312361253610475399",       # Finance Cart
    "cart": "5312361253610475399",
    "🛍️": "5294167145079395967",      # Finance Shopping Bag
    "🛍": "5294167145079395967",
    "📦": "5445221832074483553",       # Finance Briefcase / Package
    "package": "5445221832074483553",
    "box": "6206236607532504295",
    "📢": "6206080502651164081",
    "updates": "6206080502651164081",
    "🔔": "6325601063017648133",       # Erangle Animated Bell
    "bell": "6325601063017648133",
    "✨": "6325413811033477368",       # Erangle Animated Sparkles
    "sparkle": "6325413811033477368",
    "💡": "6325413811033477368",       # Animated Sparkles for Tips / Ideas
    "tip": "6325413811033477368",
    "idea": "6325413811033477368",
    "🚀": "5195033767969839232",       # Finance Rocket
    "rocket": "5195033767969839232",
    "📱": "6325538094502123136",       # Erangle Animated Mobile
    "mobile": "6325538094502123136",
    "📲": "6325330308279308485",       # Erangle Animated Mobile OTP
    "otp_phone": "6325330308279308485",
    "📥": "5443127283898405358",       # Finance Download / Inbox
    "download": "5443127283898405358",
    "📤": "5445355530111437729",       # Finance Upload
    "upload": "5445355530111437729",
    "💬": "5303138782004924588",       # Finance Chat / Support
    "support": "5303138782004924588",

    # Status / Alerts / Checks
    "✅": "6325382986053193737",       # Erangle Animated Checkmark
    "check": "6325382986053193737",
    "check_2": "6325794886301783662",
    "check_3": "6325550279324341560",
    "check_4": "6325731183346847448",
    "check_5": "6325515305405648559",
    "check_6": "6325685188542076059",
    "check_7": "6325645228166353066",
    "✔️": "6325551537749760060",
    "check_mark": "6325551537749760060",
    "❌": "6325844463109280731",       # Erangle Animated Red Cross
    "cross": "6325844463109280731",
    "cross_2": "6325829258925052515",
    "cross_3": "6325549467575521430",
    "⚠️": "6206174450765796040",       # Warning
    "warning": "6206174450765796040",
    "warning_2": "6206077285720659346",
    "🚫": "6323406678326776083",       # Erangle Animated Prohibited
    "prohibited": "6323406678326776083",
    "⛔️": "6206285149252883826",
    "no_entry": "6206285149252883826",
    "⁉️": "6203722870548338074",
    "interrobang": "6203722870548338074",
    "❓": "6206306186002698906",
    "question": "6206306186002698906",
    "question_2": "6206003549722122915",
    "⌛": "6206118633370818254",
    "hourglass": "6206118633370818254",
    "🔄": "6325541629260206557",       # Erangle Animated Refresh / Sync
    "refresh": "6325541629260206557",
    "🛡": "6325790127478018778",       # Erangle Animated Shield
    "shield": "6325790127478018778",
    "shield_2": "6323584313879171543",
    "🔴": "6325641255321604342",       # Erangle Animated Red Dot
    "red_circle": "6325641255321604342",
    "🟢": "6323079032451634398",       # Erangle Animated Green Dot
    "green_circle": "6323079032451634398",
    "🟥": "6203773684306418660",
    "red_square": "6203773684306418660",

    # Navigation & Actions
    "🔙": "6206505206197261313",
    "back": "6206505206197261313",
    "⬅️": "6206505206197261313",
    "⬅": "6206505206197261313",
    "◀️": "6206505206197261313",
    "◀": "6206505206197261313",
    "arrow_left": "6206505206197261313",
    "arrow_left_2": "6206505206197261313",
    "➡️": "6206325217002788818",
    "arrow_right": "6206325217002788818",
    "arrow_right_2": "6305547117683283307",
    "⬇️": "6204177183598974956",
    "arrow_down": "6204177183598974956",
    "arrow_down_2": "6206172741368813487",
    "⬆️": "6206046503690048595",
    "arrow_up": "6206046503690048595",
    "🔼": "6206156111255443036",
    "triangle_up": "6206156111255443036",
    "🔽": "6206368810920841771",
    "triangle_down": "6206368810920841771",
    "▶️": "6206141323683042874",
    "play": "6206141323683042874",
    "➕": "6206375377925839184",
    "plus": "6206375377925839184",
    "plus_2": "6203946234617535298",
    "plus_3": "6307589529251354537",
    "➖": "6206302088603900186",
    "minus": "6206302088603900186",
    "🗑": "6206108815075579644",
    "trash": "6206108815075579644",
    "🔍": "6206446249181189526",
    "search": "6206446249181189526",
    "🔗": "6206497372176913599",
    "link": "6206497372176913599",
    "link_2": "6305349287194662922",
    "📥": "6203886371363364022",
    "inbox": "6203886371363364022",
    "✉️": "6206112371308500200",
    "mail": "6206112371308500200",
    "🔔": "6206508629286196237",
    "bell": "6206508629286196237",
    "bell_2": "6204010762206189094",
    "📣": "6206080502651164081",
    "speaker": "6206080502651164081",
    "📌": "6206190608432764318",
    "pin": "6206190608432764318",
    "📍": "6206306078628517653",
    "location": "6206306078628517653",
    "🔖": "6206139863394162614",
    "bookmark": "6206139863394162614",
    "✏️": "6204162490515855272",
    "edit": "6204162490515855272",
    "✍️": "6307367466557249731",
    "write": "6307367466557249731",
    "📸": "6307657101971822800",
    "camera": "6307657101971822800",
    "🖼": "6203941179441028086",
    "image": "6203941179441028086",
    "image_2": "6305306066938763236",
    "🗓": "6206344711859345194",
    "calendar": "6206344711859345194",
    "🕰": "6325746606574407829",       # Clock
    "⏰": "6325746606574407829",
    "clock": "6325746606574407829",
    "🛰️": "6206515969385308049",       # Satellite / Radar
    "🛰": "6206515969385308049",
    "satellite": "6206515969385308049",
    "🏠": "6305157130357839863",
    "home": "6305157130357839863",
    "📖": "6307686831735444755",
    "book": "6307686831735444755",
    "📞": "6204108584381322968",
    "phone": "6204108584381322968",
    "phone_2": "6307630477469554438",
    "📱": "6325538094502123136",       # Erangle Animated Mobile
    "mobile": "6325538094502123136",
    "mobile_2": "6206131247689766524",
    "👤": "6307777408300753473",
    "user": "6307777408300753473",
    "user_2": "6307589808424228455",
    "💼": "6206236607532504295",
    "briefcase": "6206236607532504295",
    "🛍": "6205984948218762570",
    "shopping": "6205984948218762570",
    "🎁": "6206027872121918710",
    "gift": "6206027872121918710",
    "gift_2": "6206326050226444066",
    "gift_3": "6307351429149365689",
    "🌐": "6325529375718510567",       # Animated Globe
    "globe": "6325529375718510567",
    "globe_fb": "6206117641233373098",
    "globe_2": "6206207290085741739",
    "globe_3": "6206493566835889826",
    "globe_4": "6206293004748068499",
    "globe_5": "6206141766064674936",
    "globe_6": "6206007685775628557",
    "globe_7": "6205969082609572674",
    "📈": "6325797905663791037",       # Erangle Animated Trending Chart Up
    "chart_up": "6325797905663791037",
    "📉": "6325409812418924375",       # Erangle Animated Chart Down
    "chart_down": "6325409812418924375",
    "📊": "6325667390197600621",       # Erangle Animated Bar Chart
    "bar_chart": "6325667390197600621",
    "📶": "6206515969385308049",
    "signal": "6206515969385308049",
    "🛫": "6307531091926325405",
    "airplane": "6307531091926325405",
    "📺": "6206459941536930811",
    "tv": "6206459941536930811",
    "tv_2": "6206122885388441054",
    "tv_3": "6307772013821826724",
    "🎬": "6206324353714362524",
    "clapper": "6206324353714362524",
    "🎵": "6325708780797432188",       # Erangle Animated Music
    "music": "6325708780797432188",
    "🎨": "6307647373870897360",
    "palette": "6307647373870897360",
    "🖌": "6307815809603343493",
    "brush": "6307815809603343493",
    "👑": "6325564362522104416",       # Erangle Animated Crown
    "crown": "6325564362522104416",
    "crown_2": "6206319341487527808",
    "crown_3": "6305349965799496443",
    "⭐️": "6325615025956328299",       # Erangle Animated Gold Star
    "⭐": "6325615025956328299",
    "star": "6325615025956328299",
    "star_2": "6325549480460423225",
    "star_3": "6325347178910847779",
    "🌟": "6325615025956328299",       # Erangle Animated Gold Star
    "sparkles": "6325413811033477368",
    "💫": "6206105718404159948",
    "dizzy": "6206105718404159948",
    "💯": "6325437703936545404",       # Erangle Animated 100
    "hundred": "6325437703936545404",
    "🔝": "6325405659185549712",       # Erangle Animated TOP
    "top": "6325405659185549712",
    "🆓": "6325864460477010488",       # Erangle Animated FREE
    "free": "6325864460477010488",
    "🥇": "6206419981161211268",
    "medal_1st": "6206419981161211268",
    "🥈": "6206222099132978580",
    "medal_2nd": "6206222099132978580",
    "🥉": "6206311275538946838",
    "medal_3rd": "6206311275538946838",
    "👍": "6206122090819490939",
    "thumbs_up": "6206122090819490939",
    "thumbs_up_2": "6203846376627901478",
    "🎉": "6206378324273403309",
    "party": "6206378324273403309",
    "💠": "6205965994528086727",
    "diamond_shape": "6205965994528086727",
    "☄️": "6204104220694550861",
    "comet": "6204104220694550861",
    "❤️🔥": "6206041890895172990",
    "fire_heart": "6206041890895172990",
    "🔸": "6307313006371936255",
    "diamond_orange": "6307313006371936255",

    # Keypad Digits
    "1️⃣": "6206131290639439676",
    "2️⃣": "6204065183736799071",
    "3️⃣": "6206065281287066945",
    "4️⃣": "6206163395519978583",
    "5️⃣": "6206022615081949587",
    "6️⃣": "6206288963183843221",
    "7️⃣": "6206207148351820511",
    "8️⃣": "6206050326210942294",
    "9️⃣": "6205978299609388443",
    "0️⃣": "6206095818504540991",

    # Faces & Expressions
    "😄": "6206150489143252478",
    "😀": "6206465524994414050",
    "☺️": "6206267591426578467",
    "🙂": "6206212212118263684",
    "🙂_2": "6307794927472350845",
    "😏": "6206187967027879811",
    "😏_2": "6307542847251814164",
    "🤨": "6206146095391709291",
    "😍": "6307556835960297612",
    "🥹": "6307332200580782185",
    "😬": "6206029267986289507",
    "🫣": "6205971827093673899",
    "🫣_2": "6204258641948709837",
    "🥵": "6206283388316293287",
    "🙁": "6307492879602292113",
    "👀": "6206366384264320881",
    "eyes": "6206366384264320881",
    "🫦": "6206074176164336417",
    "🧠": "6204039972278770469",
    "brain": "6204039972278770469",
    "🐾": "6206438634204174508",
    "paws": "6206438634204174508",
    "🕯": "6206145726024520937",
    "candle": "6206145726024520937",
    "💬": "6206495649895028694",
    "chat": "6206495649895028694",
    "💭": "6206503415195899956",
    "thought": "6206503415195899956",
    "thought_2": "6206516544910923492",
    "⛏": "6206188632747808299",
    "pickaxe": "6206188632747808299",
    "🍽": "6206295285375703410",
    "plate": "6206295285375703410",
    "🔞": "6206293296805844963",
    "adult": "6206293296805844963",
    "🖕": "6203961163923855531",
    "middle_finger": "6203961163923855531",
    "middle_finger_2": "6206192575527785656",
    "✌️": "6204087066595171188",
    "peace": "6204087066595171188",
    "〽️": "6206007930588762926",
    "part_alternation": "6206007930588762926",
    "🙋": "6206254612035409256",
    "raising_hand": "6206254612035409256",
    "🔤": "6203791499830762189",
    "abc": "6203791499830762189",
    "🅱": "6206116515951941744",
}


def get_ui_emoji_id(key: str) -> str | None:
    """Get custom emoji ID for a UI icon, symbol, or name."""
    if not key:
        return None
    k = key.strip()
    return UI_CUSTOM_EMOJIS.get(k) or UI_CUSTOM_EMOJIS.get(k.lower())


def ui_emoji(key: str, default_char: str = "", html: bool = True) -> str:
    """Return <tg-emoji> HTML or standard unicode character for UI icons."""
    emoji_id = get_ui_emoji_id(key)
    char = default_char if default_char else key
    if html and emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{char}</tg-emoji>'
    return char


# ═══════════════════════════════════════════════════════════════════
# UNIVERSAL AUTOMATIC CUSTOM EMOJI FORMATTER & KEYBOARD ENHANCER
# ═══════════════════════════════════════════════════════════════════
_GLOBAL_EMOJI_MAP: dict[str, str] = {}
_EMOJI_REGEX = None
_ANY_EMOJI_REGEX = None


def _init_global_emoji_map():
    global _GLOBAL_EMOJI_MAP
    if _GLOBAL_EMOJI_MAP:
        return

    import json
    import os

    # Load from all_emojis.json if present
    json_path = os.path.join(os.path.dirname(__file__), "all_emojis.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                _GLOBAL_EMOJI_MAP.update(json.load(f))
        except Exception:
            pass

    # 1. Flags
    for a2, eid in FLAG_CUSTOM_EMOJIS.items():
        if a2 != "DEFAULT" and len(a2) == 2:
            u_flag = "".join(chr(0x1F1E6 + ord(c) - ord('A')) for c in a2.upper())
            _GLOBAL_EMOJI_MAP[u_flag] = eid
            _GLOBAL_EMOJI_MAP[u_flag.replace('\ufe0f', '')] = eid
    _GLOBAL_EMOJI_MAP["🚩"] = FLAG_CUSTOM_EMOJIS.get("DEFAULT", "5294236848103643477")

    # 2. UI Emojis
    INVALID_CHARS = {'✦', '❞', '➔', '〰', 'Ⓜ', '☑'}
    for k, eid in UI_CUSTOM_EMOJIS.items():
        if not k.isascii() and '_' not in k and k not in INVALID_CHARS:
            _GLOBAL_EMOJI_MAP[k] = eid
            clean_k = k.replace('\ufe0f', '')
            if clean_k and clean_k not in INVALID_CHARS:
                _GLOBAL_EMOJI_MAP[clean_k] = eid
                _GLOBAL_EMOJI_MAP[clean_k + '\ufe0f'] = eid

    for bad in INVALID_CHARS:
        _GLOBAL_EMOJI_MAP.pop(bad, None)


def _get_emoji_regex():
    global _EMOJI_REGEX, _ANY_EMOJI_REGEX
    if _EMOJI_REGEX is None:
        _init_global_emoji_map()
        import re
        escaped_emojis = [re.escape(k) for k in sorted(_GLOBAL_EMOJI_MAP.keys(), key=len, reverse=True)]
        pattern = r"(<tg-emoji[^>]*>.*?</tg-emoji>)|(" + "|".join(escaped_emojis) + r")"
        _EMOJI_REGEX = re.compile(pattern, re.DOTALL)
        _ANY_EMOJI_REGEX = re.compile("|".join(escaped_emojis))
    return _EMOJI_REGEX


def apply_custom_emojis(text: str) -> str:
    """Automatically convert all raw unicode emojis into <tg-emoji> custom emojis if not already wrapped."""
    if not text or not isinstance(text, str):
        return text
    try:
        rx = _get_emoji_regex()

        def _repl(match):
            tg_tag = match.group(1)
            if tg_tag:
                return tg_tag
            raw_char = match.group(2)
            if raw_char and raw_char in _GLOBAL_EMOJI_MAP:
                eid = _GLOBAL_EMOJI_MAP[raw_char]
                return f'<tg-emoji emoji-id="{eid}">{raw_char}</tg-emoji>'
            return match.group(0)

        return rx.sub(_repl, text)
    except Exception:
        return text


def extract_emoji_for_button(btn_text: str) -> tuple[str | None, str]:
    """Inspect button text, return (emoji_id, clean_text) by extracting leading or trailing navigation emoji for icon."""
    if not btn_text or not isinstance(btn_text, str):
        return None, btn_text

    _get_emoji_regex()
    global _ANY_EMOJI_REGEX
    import re

    # 1. Leading emoji (e.g. '🛒 Buy', '🇮🇳 India')
    stripped = btn_text.lstrip()
    match = _ANY_EMOJI_REGEX.match(stripped) if _ANY_EMOJI_REGEX else None
    if match:
        emoji_id = _GLOBAL_EMOJI_MAP.get(match.group(0))
        if emoji_id:
            cleaned = stripped[match.end():].lstrip(' •-|:').strip()
            return emoji_id, cleaned if cleaned else btn_text

    # 2. Trailing emoji for navigation buttons (e.g. 'Next ▶️')
    # NEVER strip status indicators like ⏳ (price loading) or 🔄
    trailing = btn_text.rstrip()
    match_end = _ANY_EMOJI_REGEX.search(trailing) if _ANY_EMOJI_REGEX else None
    if match_end and match_end.end() == len(trailing):
        emoji_char = match_end.group(0)
        if emoji_char not in ('⏳', '⌛', '🔄'):
            emoji_id = _GLOBAL_EMOJI_MAP.get(emoji_char)
            if emoji_id:
                cleaned = trailing[:match_end.start()].rstrip(' •-|:').strip()
                return emoji_id, cleaned if cleaned else btn_text

    return None, btn_text


def enhance_markup(markup):
    """Recursively enhance an InlineKeyboardMarkup so buttons have custom emoji icons and clean titles."""
    if not markup:
        return markup
    try:
        from telegram import InlineKeyboardMarkup
        if isinstance(markup, InlineKeyboardMarkup) and markup.inline_keyboard:
            for row in markup.inline_keyboard:
                for btn in row:
                    eid, clean = extract_emoji_for_button(btn.text)
                    if clean:
                        btn.text = clean
    except Exception:
        pass
    return markup




