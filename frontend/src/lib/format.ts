export function money(value: string | number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value))
}

export function utcDate(value: string): string {
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC',
  }).format(new Date(value)) + ' UTC'
}

export function readPreference(key: string, fallback = ''): string {
  try { return localStorage.getItem(key) || fallback } catch { return fallback }
}

export function savePreference(key: string, value: string) {
  try { localStorage.setItem(key, value) } catch { /* Storage may be unavailable in private browsing. */ }
}

export const SUGGESTED_CATEGORIES = ['Classic Literature', 'Fiction', 'Science & Tech', 'Philosophy', 'History', 'Art & Design']

const regionNames = new Intl.DisplayNames(['en'], { type: 'region' })
const ISO_CODES = 'AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW'.split(' ')
export const COUNTRIES = ISO_CODES.map((code) => ({ code, name: regionNames.of(code) || code })).sort((a, b) => a.name.localeCompare(b.name))
export const COUNTRY_CODES = new Set(ISO_CODES)
export const countryName = (code: string) => code ? regionNames.of(code) || code : 'Unknown origin'
