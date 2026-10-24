"""
Единый справочник стран — используется везде (wizard, settings, фильтры).
Не дублируется в разных файлах. Источник — ISO 3166-1, RU/EN/UK названия, флаги, псевдонимы.
"""
from typing import List, Dict

# Специальные опции сегментации
SPECIAL_OPTIONS = [
    {"code": "ALL", "name_ru": "Все страны", "name_en": "All countries", "name_uk": "Всі країни", "flag": "🌍", "aliases": ["все", "all", "всі"]},
    {"code": "NOT_SPECIFIED", "name_ru": "Не указана", "name_en": "Not specified", "name_uk": "Не вказано", "flag": "❓", "aliases": ["не указана", "не вказано", "not specified", "unknown"]},
]

COUNTRIES: List[Dict] = [
    {"code": "AF", "iso3": "AFG", "name_ru": "Афганистан", "name_en": "Afghanistan", "name_uk": "Афганістан", "flag": "🇦🇫", "aliases": ["афганистан", "afghanistan", "af"]},
    {"code": "AL", "iso3": "ALB", "name_ru": "Албания", "name_en": "Albania", "name_uk": "Албанія", "flag": "🇦🇱", "aliases": ["албания", "albania", "al"]},
    {"code": "DZ", "iso3": "DZA", "name_ru": "Алжир", "name_en": "Algeria", "name_uk": "Алжир", "flag": "🇩🇿", "aliases": ["алжир", "algeria"]},
    {"code": "AD", "iso3": "AND", "name_ru": "Андорра", "name_en": "Andorra", "name_uk": "Андорра", "flag": "🇦🇩", "aliases": ["андорра", "andorra"]},
    {"code": "AO", "iso3": "AGO", "name_ru": "Ангола", "name_en": "Angola", "name_uk": "Ангола", "flag": "🇦🇴", "aliases": ["ангола", "angola"]},
    {"code": "AI", "iso3": "AIA", "name_ru": "Ангилья", "name_en": "Anguilla", "name_uk": "Ангілья", "flag": "🇦🇮", "aliases": ["ангилья", "anguilla"]},
    {"code": "AG", "iso3": "ATG", "name_ru": "Антигуа и Барбуда", "name_en": "Antigua and Barbuda", "name_uk": "Антигуа і Барбуда", "flag": "🇦🇬", "aliases": ["антигуа", "antigua"]},
    {"code": "AR", "iso3": "ARG", "name_ru": "Аргентина", "name_en": "Argentina", "name_uk": "Аргентина", "flag": "🇦🇷", "aliases": ["аргентина", "argentina", "ar"]},
    {"code": "AM", "iso3": "ARM", "name_ru": "Армения", "name_en": "Armenia", "name_uk": "Вірменія", "flag": "🇦🇲", "aliases": ["армения", "армения", "armenia", "вірменія"]},
    {"code": "AW", "iso3": "ABW", "name_ru": "Аруба", "name_en": "Aruba", "name_uk": "Аруба", "flag": "🇦🇼", "aliases": ["аруба", "aruba"]},
    {"code": "AU", "iso3": "AUS", "name_ru": "Австралия", "name_en": "Australia", "name_uk": "Австралія", "flag": "🇦🇺", "aliases": ["австралия", "australia", "австралія"]},
    {"code": "AT", "iso3": "AUT", "name_ru": "Австрия", "name_en": "Austria", "name_uk": "Австрія", "flag": "🇦🇹", "aliases": ["австрия", "austria", "австрія"]},
    {"code": "AZ", "iso3": "AZE", "name_ru": "Азербайджан", "name_en": "Azerbaijan", "name_uk": "Азербайджан", "flag": "🇦🇿", "aliases": ["азербайджан", "azerbaijan"]},
    {"code": "BS", "iso3": "BHS", "name_ru": "Багамы", "name_en": "Bahamas", "name_uk": "Багами", "flag": "🇧🇸", "aliases": ["багамы", "bahamas"]},
    {"code": "BH", "iso3": "BHR", "name_ru": "Бахрейн", "name_en": "Bahrain", "name_uk": "Бахрейн", "flag": "🇧🇭", "aliases": ["бахрейн", "bahrain"]},
    {"code": "BD", "iso3": "BGD", "name_ru": "Бангладеш", "name_en": "Bangladesh", "name_uk": "Бангладеш", "flag": "🇧🇩", "aliases": ["бангладеш", "bangladesh"]},
    {"code": "BB", "iso3": "BRB", "name_ru": "Барбадос", "name_en": "Barbados", "name_uk": "Барбадос", "flag": "🇧🇧", "aliases": ["барбадос", "barbados"]},
    {"code": "BY", "iso3": "BLR", "name_ru": "Беларусь", "name_en": "Belarus", "name_uk": "Білорусь", "flag": "🇧🇾", "aliases": ["беларусь", "belarus", "білорусь", "by"]},
    {"code": "BE", "iso3": "BEL", "name_ru": "Бельгия", "name_en": "Belgium", "name_uk": "Бельгія", "flag": "🇧🇪", "aliases": ["бельгия", "belgium", "бельгія"]},
    {"code": "BZ", "iso3": "BLZ", "name_ru": "Белиз", "name_en": "Belize", "name_uk": "Беліз", "flag": "🇧🇿", "aliases": ["белиз", "belize"]},
    {"code": "BJ", "iso3": "BEN", "name_ru": "Бенин", "name_en": "Benin", "name_uk": "Бенін", "flag": "🇧🇯", "aliases": ["бенин", "benin", "бенін"]},
    {"code": "BT", "iso3": "BTN", "name_ru": "Бутан", "name_en": "Bhutan", "name_uk": "Бутан", "flag": "🇧🇹", "aliases": ["бутан", "bhutan"]},
    {"code": "BO", "iso3": "BOL", "name_ru": "Боливия", "name_en": "Bolivia", "name_uk": "Болівія", "flag": "🇧🇴", "aliases": ["боливия", "bolivia"]},
    {"code": "BA", "iso3": "BIH", "name_ru": "Босния и Герцеговина", "name_en": "Bosnia and Herzegovina", "name_uk": "Боснія і Герцеговина", "flag": "🇧🇦", "aliases": ["босния", "bosnia"]},
    {"code": "BW", "iso3": "BWA", "name_ru": "Ботсвана", "name_en": "Botswana", "name_uk": "Ботсвана", "flag": "🇧🇼", "aliases": ["ботсвана", "botswana"]},
    {"code": "BR", "iso3": "BRA", "name_ru": "Бразилия", "name_en": "Brazil", "name_uk": "Бразилія", "flag": "🇧🇷", "aliases": ["бразилия", "brazil", "бразилія", "br"]},
    {"code": "BN", "iso3": "BRN", "name_ru": "Бруней", "name_en": "Brunei", "name_uk": "Бруней", "flag": "🇧🇳", "aliases": ["бруней", "brunei"]},
    {"code": "BG", "iso3": "BGR", "name_ru": "Болгария", "name_en": "Bulgaria", "name_uk": "Болгарія", "flag": "🇧🇬", "aliases": ["болгария", "bulgaria", "болгарія"]},
    {"code": "BF", "iso3": "BFA", "name_ru": "Буркина-Фасо", "name_en": "Burkina Faso", "name_uk": "Буркіна-Фасо", "flag": "🇧🇫", "aliases": ["буркина", "burkina"]},
    {"code": "BI", "iso3": "BDI", "name_ru": "Бурунди", "name_en": "Burundi", "name_uk": "Бурунді", "flag": "🇧🇮", "aliases": ["бурунди", "burundi"]},
    {"code": "KH", "iso3": "KHM", "name_ru": "Камбоджа", "name_en": "Cambodia", "name_uk": "Камбоджа", "flag": "🇰🇭", "aliases": ["камбоджа", "cambodia"]},
    {"code": "CM", "iso3": "CMR", "name_ru": "Камерун", "name_en": "Cameroon", "name_uk": "Камерун", "flag": "🇨🇲", "aliases": ["камерун", "cameroon"]},
    {"code": "CA", "iso3": "CAN", "name_ru": "Канада", "name_en": "Canada", "name_uk": "Канада", "flag": "🇨🇦", "aliases": ["канада", "canada", "ca"]},
    {"code": "CV", "iso3": "CPV", "name_ru": "Кабо-Верде", "name_en": "Cape Verde", "name_uk": "Кабо-Верде", "flag": "🇨🇻", "aliases": ["кабо-верде", "cape verde"]},
    {"code": "CF", "iso3": "CAF", "name_ru": "ЦАР", "name_en": "Central African Republic", "name_uk": "ЦАР", "flag": "🇨🇫", "aliases": ["цар", "центральноафриканская республика", "central african republic"]},
    {"code": "TD", "iso3": "TCD", "name_ru": "Чад", "name_en": "Chad", "name_uk": "Чад", "flag": "🇹🇩", "aliases": ["чад", "chad"]},
    {"code": "CL", "iso3": "CHL", "name_ru": "Чили", "name_en": "Chile", "name_uk": "Чилі", "flag": "🇨🇱", "aliases": ["чили", "chile", "чилі"]},
    {"code": "CN", "iso3": "CHN", "name_ru": "Китай", "name_en": "China", "name_uk": "Китай", "flag": "🇨🇳", "aliases": ["китай", "china", "cn"]},
    {"code": "CO", "iso3": "COL", "name_ru": "Колумбия", "name_en": "Colombia", "name_uk": "Колумбія", "flag": "🇨🇴", "aliases": ["колумбия", "colombia"]},
    {"code": "KM", "iso3": "COM", "name_ru": "Коморы", "name_en": "Comoros", "name_uk": "Комори", "flag": "🇰🇲", "aliases": ["коморы", "comoros"]},
    {"code": "CG", "iso3": "COG", "name_ru": "Конго", "name_en": "Congo", "name_uk": "Конго", "flag": "🇨🇬", "aliases": ["конго", "congo"]},
    {"code": "CD", "iso3": "COD", "name_ru": "ДР Конго", "name_en": "DR Congo", "name_uk": "ДР Конго", "flag": "🇨🇩", "aliases": ["др конго", "drc", "демократическая республика конго"]},
    {"code": "CR", "iso3": "CRI", "name_ru": "Коста-Рика", "name_en": "Costa Rica", "name_uk": "Коста-Рика", "flag": "🇨🇷", "aliases": ["коста-рика", "costa rica"]},
    {"code": "HR", "iso3": "HRV", "name_ru": "Хорватия", "name_en": "Croatia", "name_uk": "Хорватія", "flag": "🇭🇷", "aliases": ["хорватия", "croatia", "хорватія"]},
    {"code": "CU", "iso3": "CUB", "name_ru": "Куба", "name_en": "Cuba", "name_uk": "Куба", "flag": "🇨🇺", "aliases": ["куба", "cuba"]},
    {"code": "CY", "iso3": "CYP", "name_ru": "Кипр", "name_en": "Cyprus", "name_uk": "Кіпр", "flag": "🇨🇾", "aliases": ["кипр", "cyprus", "кіпр"]},
    {"code": "CZ", "iso3": "CZE", "name_ru": "Чехия", "name_en": "Czech Republic", "name_uk": "Чехія", "flag": "🇨🇿", "aliases": ["чехия", "czech", "чехія", "czechia"]},
    {"code": "DK", "iso3": "DNK", "name_ru": "Дания", "name_en": "Denmark", "name_uk": "Данія", "flag": "🇩🇰", "aliases": ["дания", "denmark", "данія"]},
    {"code": "DJ", "iso3": "DJI", "name_ru": "Джибути", "name_en": "Djibouti", "name_uk": "Джибуті", "flag": "🇩🇯", "aliases": ["джибути", "djibouti"]},
    {"code": "DM", "iso3": "DMA", "name_ru": "Доминика", "name_en": "Dominica", "name_uk": "Домініка", "flag": "🇩🇲", "aliases": ["доминика", "dominica"]},
    {"code": "DO", "iso3": "DOM", "name_ru": "Доминикана", "name_en": "Dominican Republic", "name_uk": "Домінікани", "flag": "🇩🇴", "aliases": ["доминикана", "dominican republic"]},
    {"code": "EC", "iso3": "ECU", "name_ru": "Эквадор", "name_en": "Ecuador", "name_uk": "Еквадор", "flag": "🇪🇨", "aliases": ["эквадор", "ecuador"]},
    {"code": "EG", "iso3": "EGY", "name_ru": "Египет", "name_en": "Egypt", "name_uk": "Єгипет", "flag": "🇪🇬", "aliases": ["египет", "egypt", "єгипет"]},
    {"code": "SV", "iso3": "SLV", "name_ru": "Сальвадор", "name_en": "El Salvador", "name_uk": "Сальвадор", "flag": "🇸🇻", "aliases": ["сальвадор", "el salvador"]},
    {"code": "GQ", "iso3": "GNQ", "name_ru": "Экваториальная Гвинея", "name_en": "Equatorial Guinea", "name_uk": "Екваторіальна Гвінея", "flag": "🇬🇶", "aliases": ["экваториальная гвинея", "equatorial guinea"]},
    {"code": "ER", "iso3": "ERI", "name_ru": "Эритрея", "name_en": "Eritrea", "name_uk": "Еритрея", "flag": "🇪🇷", "aliases": ["эритрея", "eritrea"]},
    {"code": "EE", "iso3": "EST", "name_ru": "Эстония", "name_en": "Estonia", "name_uk": "Естонія", "flag": "🇪🇪", "aliases": ["эстония", "estonia", "естонія", "ee", "est"]},
    {"code": "SZ", "iso3": "SWZ", "name_ru": "Эсватини", "name_en": "Eswatini", "name_uk": "Есватіні", "flag": "🇸🇿", "aliases": ["эсватини", "eswatini", "сватини"]},
    {"code": "ET", "iso3": "ETH", "name_ru": "Эфиопия", "name_en": "Ethiopia", "name_uk": "Ефіопія", "flag": "🇪🇹", "aliases": ["эфиопия", "ethiopia", "ефіопія"]},
    {"code": "FJ", "iso3": "FJI", "name_ru": "Фиджи", "name_en": "Fiji", "name_uk": "Фіджі", "flag": "🇫🇯", "aliases": ["фиджи", "fiji"]},
    {"code": "FI", "iso3": "FIN", "name_ru": "Финляндия", "name_en": "Finland", "name_uk": "Фінляндія", "flag": "🇫🇮", "aliases": ["финляндия", "finland", "фінляндія"]},
    {"code": "FR", "iso3": "FRA", "name_ru": "Франция", "name_en": "France", "name_uk": "Франція", "flag": "🇫🇷", "aliases": ["франция", "france", "франція", "fr"]},
    {"code": "GA", "iso3": "GAB", "name_ru": "Габон", "name_en": "Gabon", "name_uk": "Габон", "flag": "🇬🇦", "aliases": ["габон", "gabon"]},
    {"code": "GM", "iso3": "GMB", "name_ru": "Гамбия", "name_en": "Gambia", "name_uk": "Гамбія", "flag": "🇬🇲", "aliases": ["гамбия", "gambia"]},
    {"code": "GE", "iso3": "GEO", "name_ru": "Грузия", "name_en": "Georgia", "name_uk": "Грузія", "flag": "🇬🇪", "aliases": ["грузия", "georgia", "грузія"]},
    {"code": "DE", "iso3": "DEU", "name_ru": "Германия", "name_en": "Germany", "name_uk": "Німеччина", "flag": "🇩🇪", "aliases": ["германия", "germany", "німеччина", "deutschland", "de", "ger"]},
    {"code": "GH", "iso3": "GHA", "name_ru": "Гана", "name_en": "Ghana", "name_uk": "Гана", "flag": "🇬🇭", "aliases": ["гана", "ghana"]},
    {"code": "GR", "iso3": "GRC", "name_ru": "Греция", "name_en": "Greece", "name_uk": "Греція", "flag": "🇬🇷", "aliases": ["греция", "greece", "греція"]},
    {"code": "GD", "iso3": "GRD", "name_ru": "Гренада", "name_en": "Grenada", "name_uk": "Гренада", "flag": "🇬🇩", "aliases": ["гренада", "grenada"]},
    {"code": "GT", "iso3": "GTM", "name_ru": "Гватемала", "name_en": "Guatemala", "name_uk": "Гватемала", "flag": "🇬🇹", "aliases": ["гватемала", "guatemala"]},
    {"code": "GN", "iso3": "GIN", "name_ru": "Гвинея", "name_en": "Guinea", "name_uk": "Гвінея", "flag": "🇬🇳", "aliases": ["гвинея", "guinea"]},
    {"code": "GW", "iso3": "GNB", "name_ru": "Гвинея-Бисау", "name_en": "Guinea-Bissau", "name_uk": "Гвінея-Бісау", "flag": "🇬🇼", "aliases": ["гвинея-бисау", "guinea-bissau"]},
    {"code": "GY", "iso3": "GUY", "name_ru": "Гайана", "name_en": "Guyana", "name_uk": "Гаяна", "flag": "🇬🇾", "aliases": ["гайана", "guyana"]},
    {"code": "HT", "iso3": "HTI", "name_ru": "Гаити", "name_en": "Haiti", "name_uk": "Гаїті", "flag": "🇭🇹", "aliases": ["гаити", "haiti"]},
    {"code": "HN", "iso3": "HND", "name_ru": "Гондурас", "name_en": "Honduras", "name_uk": "Гондурас", "flag": "🇭🇳", "aliases": ["гондурас", "honduras"]},
    {"code": "HU", "iso3": "HUN", "name_ru": "Венгрия", "name_en": "Hungary", "name_uk": "Угорщина", "flag": "🇭🇺", "aliases": ["венгрия", "hungary", "угорщина", "magyarorszag"]},
    {"code": "IS", "iso3": "ISL", "name_ru": "Исландия", "name_en": "Iceland", "name_uk": "Ісландія", "flag": "🇮🇸", "aliases": ["исландия", "iceland", "ісландія"]},
    {"code": "IN", "iso3": "IND", "name_ru": "Индия", "name_en": "India", "name_uk": "Індія", "flag": "🇮🇳", "aliases": ["индия", "india", "індія", "in"]},
    {"code": "ID", "iso3": "IDN", "name_ru": "Индонезия", "name_en": "Indonesia", "name_uk": "Індонезія", "flag": "🇮🇩", "aliases": ["индонезия", "indonesia", "індонезія"]},
    {"code": "IR", "iso3": "IRN", "name_ru": "Иран", "name_en": "Iran", "name_uk": "Іран", "flag": "🇮🇷", "aliases": ["иран", "iran"]},
    {"code": "IQ", "iso3": "IRQ", "name_ru": "Ирак", "name_en": "Iraq", "name_uk": "Ірак", "flag": "🇮🇶", "aliases": ["ирак", "iraq"]},
    {"code": "IE", "iso3": "IRL", "name_ru": "Ирландия", "name_en": "Ireland", "name_uk": "Ірландія", "flag": "🇮🇪", "aliases": ["ирландия", "ireland", "ірландія"]},
    {"code": "IL", "iso3": "ISR", "name_ru": "Израиль", "name_en": "Israel", "name_uk": "Ізраїль", "flag": "🇮🇱", "aliases": ["израиль", "israel", "ізраїль"]},
    {"code": "IT", "iso3": "ITA", "name_ru": "Италия", "name_en": "Italy", "name_uk": "Італія", "flag": "🇮🇹", "aliases": ["италия", "italy", "італія", "it"]},
    {"code": "JM", "iso3": "JAM", "name_ru": "Ямайка", "name_en": "Jamaica", "name_uk": "Ямайка", "flag": "🇯🇲", "aliases": ["ямайка", "jamaica"]},
    {"code": "JP", "iso3": "JPN", "name_ru": "Япония", "name_en": "Japan", "name_uk": "Японія", "flag": "🇯🇵", "aliases": ["япония", "japan", "японія", "jp", "nippon"]},
    {"code": "JO", "iso3": "JOR", "name_ru": "Иордания", "name_en": "Jordan", "name_uk": "Йорданія", "flag": "🇯🇴", "aliases": ["иордания", "jordan", "йорданія"]},
    {"code": "KZ", "iso3": "KAZ", "name_ru": "Казахстан", "name_en": "Kazakhstan", "name_uk": "Казахстан", "flag": "🇰🇿", "aliases": ["казахстан", "kazakhstan", "kz"]},
    {"code": "KE", "iso3": "KEN", "name_ru": "Кения", "name_en": "Kenya", "name_uk": "Кенія", "flag": "🇰🇪", "aliases": ["кения", "kenya", "кенія"]},
    {"code": "KI", "iso3": "KIR", "name_ru": "Кирибати", "name_en": "Kiribati", "name_uk": "Кірибаті", "flag": "🇰🇮", "aliases": ["кирибати", "kiribati"]},
    {"code": "KP", "iso3": "PRK", "name_ru": "КНДР", "name_en": "North Korea", "name_uk": "КНДР", "flag": "🇰🇵", "aliases": ["кндр", "северная корея", "north korea", "dprk"]},
    {"code": "KR", "iso3": "KOR", "name_ru": "Южная Корея", "name_en": "South Korea", "name_uk": "Південна Корея", "flag": "🇰🇷", "aliases": ["южная корея", "south korea", "південна корея", "korea", "kr"]},
    {"code": "KW", "iso3": "KWT", "name_ru": "Кувейт", "name_en": "Kuwait", "name_uk": "Кувейт", "flag": "🇰🇼", "aliases": ["кувейт", "kuwait"]},
    {"code": "KG", "iso3": "KGZ", "name_ru": "Кыргызстан", "name_en": "Kyrgyzstan", "name_uk": "Киргизстан", "flag": "🇰🇬", "aliases": ["кыргызстан", "kyrgyzstan", "киргизстан"]},
    {"code": "LA", "iso3": "LAO", "name_ru": "Лаос", "name_en": "Laos", "name_uk": "Лаос", "flag": "🇱🇦", "aliases": ["лаос", "laos"]},
    {"code": "LV", "iso3": "LVA", "name_ru": "Латвия", "name_en": "Latvia", "name_uk": "Латвія", "flag": "🇱🇻", "aliases": ["латвия", "latvia", "латвія"]},
    {"code": "LB", "iso3": "LBN", "name_ru": "Ливан", "name_en": "Lebanon", "name_uk": "Ліван", "flag": "🇱🇧", "aliases": ["ливан", "lebanon", "ліван"]},
    {"code": "LS", "iso3": "LSO", "name_ru": "Лесото", "name_en": "Lesotho", "name_uk": "Лесото", "flag": "🇱🇸", "aliases": ["лесото", "lesotho"]},
    {"code": "LR", "iso3": "LBR", "name_ru": "Либерия", "name_en": "Liberia", "name_uk": "Ліберія", "flag": "🇱🇷", "aliases": ["либерия", "liberia"]},
    {"code": "LY", "iso3": "LBY", "name_ru": "Ливия", "name_en": "Libya", "name_uk": "Лівія", "flag": "🇱🇾", "aliases": ["ливия", "libya", "лівія"]},
    {"code": "LI", "iso3": "LIE", "name_ru": "Лихтенштейн", "name_en": "Liechtenstein", "name_uk": "Ліхтенштейн", "flag": "🇱🇮", "aliases": ["лихтенштейн", "liechtenstein"]},
    {"code": "LT", "iso3": "LTU", "name_ru": "Литва", "name_en": "Lithuania", "name_uk": "Литва", "flag": "🇱🇹", "aliases": ["литва", "lithuania", "lt"]},
    {"code": "LU", "iso3": "LUX", "name_ru": "Люксембург", "name_en": "Luxembourg", "name_uk": "Люксембург", "flag": "🇱🇺", "aliases": ["люксембург", "luxembourg"]},
    {"code": "MG", "iso3": "MDG", "name_ru": "Мадагаскар", "name_en": "Madagascar", "name_uk": "Мадагаскар", "flag": "🇲🇬", "aliases": ["мадагаскар", "madagascar"]},
    {"code": "MW", "iso3": "MWI", "name_ru": "Малави", "name_en": "Malawi", "name_uk": "Малаві", "flag": "🇲🇼", "aliases": ["малави", "malawi"]},
    {"code": "MY", "iso3": "MYS", "name_ru": "Малайзия", "name_en": "Malaysia", "name_uk": "Малайзія", "flag": "🇲🇾", "aliases": ["малайзия", "malaysia", "малайзія"]},
    {"code": "MV", "iso3": "MDV", "name_ru": "Мальдивы", "name_en": "Maldives", "name_uk": "Мальдіви", "flag": "🇲🇻", "aliases": ["мальдивы", "maldives", "мальдіви"]},
    {"code": "ML", "iso3": "MLI", "name_ru": "Мали", "name_en": "Mali", "name_uk": "Малі", "flag": "🇲🇱", "aliases": ["мали", "mali"]},
    {"code": "MT", "iso3": "MLT", "name_ru": "Мальта", "name_en": "Malta", "name_uk": "Мальта", "flag": "🇲🇹", "aliases": ["мальта", "malta"]},
    {"code": "MH", "iso3": "MHL", "name_ru": "Маршалловы Острова", "name_en": "Marshall Islands", "name_uk": "Маршаллові Острови", "flag": "🇲🇭", "aliases": ["маршалловы острова", "marshall islands"]},
    {"code": "MR", "iso3": "MRT", "name_ru": "Мавритания", "name_en": "Mauritania", "name_uk": "Мавританія", "flag": "🇲🇷", "aliases": ["мавритания", "mauritania"]},
    {"code": "MU", "iso3": "MUS", "name_ru": "Маврикий", "name_en": "Mauritius", "name_uk": "Маврикій", "flag": "🇲🇺", "aliases": ["маврикий", "mauritius"]},
    {"code": "MX", "iso3": "MEX", "name_ru": "Мексика", "name_en": "Mexico", "name_uk": "Мексика", "flag": "🇲🇽", "aliases": ["мексика", "mexico", "mx"]},
    {"code": "FM", "iso3": "FSM", "name_ru": "Микронезия", "name_en": "Micronesia", "name_uk": "Мікронезія", "flag": "🇫🇲", "aliases": ["микронезия", "micronesia"]},
    {"code": "MD", "iso3": "MDA", "name_ru": "Молдова", "name_en": "Moldova", "name_uk": "Молдова", "flag": "🇲🇩", "aliases": ["молдова", "moldova", "md"]},
    {"code": "MC", "iso3": "MCO", "name_ru": "Монако", "name_en": "Monaco", "name_uk": "Монако", "flag": "🇲🇨", "aliases": ["монако", "monaco"]},
    {"code": "MN", "iso3": "MNG", "name_ru": "Монголия", "name_en": "Mongolia", "name_uk": "Монголія", "flag": "🇲🇳", "aliases": ["монголия", "mongolia", "монголія"]},
    {"code": "ME", "iso3": "MNE", "name_ru": "Черногория", "name_en": "Montenegro", "name_uk": "Чорногорія", "flag": "🇲🇪", "aliases": ["черногория", "montenegro", "чорногорія"]},
    {"code": "MA", "iso3": "MAR", "name_ru": "Марокко", "name_en": "Morocco", "name_uk": "Марокко", "flag": "🇲🇦", "aliases": ["марокко", "morocco"]},
    {"code": "MZ", "iso3": "MOZ", "name_ru": "Мозамбик", "name_en": "Mozambique", "name_uk": "Мозамбік", "flag": "🇲🇿", "aliases": ["мозамбик", "mozambique"]},
    {"code": "MM", "iso3": "MMR", "name_ru": "Мьянма", "name_en": "Myanmar", "name_uk": "Мʼянма", "flag": "🇲🇲", "aliases": ["мьянма", "myanmar", "бирма"]},
    {"code": "NA", "iso3": "NAM", "name_ru": "Намибия", "name_en": "Namibia", "name_uk": "Намібія", "flag": "🇳🇦", "aliases": ["намибия", "namibia"]},
    {"code": "NR", "iso3": "NRU", "name_ru": "Науру", "name_en": "Nauru", "name_uk": "Науру", "flag": "🇳🇷", "aliases": ["науру", "nauru"]},
    {"code": "NP", "iso3": "NPL", "name_ru": "Непал", "name_en": "Nepal", "name_uk": "Непал", "flag": "🇳🇵", "aliases": ["непал", "nepal"]},
    {"code": "NL", "iso3": "NLD", "name_ru": "Нидерланды", "name_en": "Netherlands", "name_uk": "Нідерланди", "flag": "🇳🇱", "aliases": ["нидерланды", "netherlands", "нідерланди", "holland", "голландия"]},
    {"code": "NZ", "iso3": "NZL", "name_ru": "Новая Зеландия", "name_en": "New Zealand", "name_uk": "Нова Зеландія", "flag": "🇳🇿", "aliases": ["новая зеландия", "new zealand", "нова зеландія"]},
    {"code": "NI", "iso3": "NIC", "name_ru": "Никарагуа", "name_en": "Nicaragua", "name_uk": "Нікарагуа", "flag": "🇳🇮", "aliases": ["никарагуа", "nicaragua"]},
    {"code": "NE", "iso3": "NER", "name_ru": "Нигер", "name_en": "Niger", "name_uk": "Нігер", "flag": "🇳🇪", "aliases": ["нигер", "niger", "нігер"]},
    {"code": "NG", "iso3": "NGA", "name_ru": "Нигерия", "name_en": "Nigeria", "name_uk": "Нігерія", "flag": "🇳🇬", "aliases": ["нигерия", "nigeria", "нігерія", "ng"]},
    {"code": "MK", "iso3": "MKD", "name_ru": "Северная Македония", "name_en": "North Macedonia", "name_uk": "Північна Македонія", "flag": "🇲🇰", "aliases": ["македония", "macedonia", "північна македонія"]},
    {"code": "NO", "iso3": "NOR", "name_ru": "Норвегия", "name_en": "Norway", "name_uk": "Норвегія", "flag": "🇳🇴", "aliases": ["норвегия", "norway", "норвегія"]},
    {"code": "OM", "iso3": "OMN", "name_ru": "Оман", "name_en": "Oman", "name_uk": "Оман", "flag": "🇴🇲", "aliases": ["оман", "oman"]},
    {"code": "PK", "iso3": "PAK", "name_ru": "Пакистан", "name_en": "Pakistan", "name_uk": "Пакистан", "flag": "🇵🇰", "aliases": ["пакистан", "pakistan", "pk"]},
    {"code": "PW", "iso3": "PLW", "name_ru": "Палау", "name_en": "Palau", "name_uk": "Палау", "flag": "🇵🇼", "aliases": ["палау", "palau"]},
    {"code": "PS", "iso3": "PSE", "name_ru": "Палестина", "name_en": "Palestine", "name_uk": "Палестина", "flag": "🇵🇸", "aliases": ["палестина", "palestine"]},
    {"code": "PA", "iso3": "PAN", "name_ru": "Панама", "name_en": "Panama", "name_uk": "Панама", "flag": "🇵🇦", "aliases": ["панама", "panama"]},
    {"code": "PG", "iso3": "PNG", "name_ru": "Папуа — Новая Гвинея", "name_en": "Papua New Guinea", "name_uk": "Папуа — Нова Гвінея", "flag": "🇵🇬", "aliases": ["папуа", "papua"]},
    {"code": "PY", "iso3": "PRY", "name_ru": "Парагвай", "name_en": "Paraguay", "name_uk": "Парагвай", "flag": "🇵🇾", "aliases": ["парагвай", "paraguay"]},
    {"code": "PE", "iso3": "PER", "name_ru": "Перу", "name_en": "Peru", "name_uk": "Перу", "flag": "🇵🇪", "aliases": ["перу", "peru"]},
    {"code": "PH", "iso3": "PHL", "name_ru": "Филиппины", "name_en": "Philippines", "name_uk": "Філіппіни", "flag": "🇵🇭", "aliases": ["филиппины", "philippines", "філіппіни"]},
    {"code": "PL", "iso3": "POL", "name_ru": "Польша", "name_en": "Poland", "name_uk": "Польща", "flag": "🇵🇱", "aliases": ["польша", "poland", "польща", "pl", "polska"]},
    {"code": "PT", "iso3": "PRT", "name_ru": "Португалия", "name_en": "Portugal", "name_uk": "Португалія", "flag": "🇵🇹", "aliases": ["португалия", "portugal", "португалія"]},
    {"code": "QA", "iso3": "QAT", "name_ru": "Катар", "name_en": "Qatar", "name_uk": "Катар", "flag": "🇶🇦", "aliases": ["катар", "qatar"]},
    {"code": "RO", "iso3": "ROU", "name_ru": "Румыния", "name_en": "Romania", "name_uk": "Румунія", "flag": "🇷🇴", "aliases": ["румыния", "romania", "румунія"]},
    {"code": "RU", "iso3": "RUS", "name_ru": "Россия", "name_en": "Russia", "name_uk": "Росія", "flag": "🇷🇺", "aliases": ["россия", "russia", "росія", "ru", "rus"]},
    {"code": "RW", "iso3": "RWA", "name_ru": "Руанда", "name_en": "Rwanda", "name_uk": "Руанда", "flag": "🇷🇼", "aliases": ["руанда", "rwanda"]},
    {"code": "KN", "iso3": "KNA", "name_ru": "Сент-Китс и Невис", "name_en": "Saint Kitts and Nevis", "name_uk": "Сент-Кітс і Невіс", "flag": "🇰🇳", "aliases": ["сент-китс", "saint kitts"]},
    {"code": "LC", "iso3": "LCA", "name_ru": "Сент-Люсия", "name_en": "Saint Lucia", "name_uk": "Сент-Люсія", "flag": "🇱🇨", "aliases": ["сент-люсия", "saint lucia"]},
    {"code": "VC", "iso3": "VCT", "name_ru": "Сент-Винсент и Гренадины", "name_en": "Saint Vincent", "name_uk": "Сент-Вінсент", "flag": "🇻🇨", "aliases": ["сент-винсент", "saint vincent"]},
    {"code": "WS", "iso3": "WSM", "name_ru": "Самоа", "name_en": "Samoa", "name_uk": "Самоа", "flag": "🇼🇸", "aliases": ["самоа", "samoa"]},
    {"code": "SM", "iso3": "SMR", "name_ru": "Сан-Марино", "name_en": "San Marino", "name_uk": "Сан-Марино", "flag": "🇸🇲", "aliases": ["сан-марино", "san marino"]},
    {"code": "ST", "iso3": "STP", "name_ru": "Сан-Томе и Принсипи", "name_en": "Sao Tome and Principe", "name_uk": "Сан-Томе і Принсіпі", "flag": "🇸🇹", "aliases": ["сан-томе", "sao tome"]},
    {"code": "SA", "iso3": "SAU", "name_ru": "Саудовская Аравия", "name_en": "Saudi Arabia", "name_uk": "Саудівська Аравія", "flag": "🇸🇦", "aliases": ["саудовская аравия", "saudi arabia", "саудівська аравія"]},
    {"code": "SN", "iso3": "SEN", "name_ru": "Сенегал", "name_en": "Senegal", "name_uk": "Сенегал", "flag": "🇸🇳", "aliases": ["сенегал", "senegal"]},
    {"code": "RS", "iso3": "SRB", "name_ru": "Сербия", "name_en": "Serbia", "name_uk": "Сербія", "flag": "🇷🇸", "aliases": ["сербия", "serbia", "сербія"]},
    {"code": "SC", "iso3": "SYC", "name_ru": "Сейшелы", "name_en": "Seychelles", "name_uk": "Сейшели", "flag": "🇸🇨", "aliases": ["сейшелы", "seychelles"]},
    {"code": "SL", "iso3": "SLE", "name_ru": "Сьерра-Леоне", "name_en": "Sierra Leone", "name_uk": "Сьєрра-Леоне", "flag": "🇸🇱", "aliases": ["сьерра-леоне", "sierra leone"]},
    {"code": "SG", "iso3": "SGP", "name_ru": "Сингапур", "name_en": "Singapore", "name_uk": "Сінгапур", "flag": "🇸🇬", "aliases": ["сингапур", "singapore", "сінгапур"]},
    {"code": "SK", "iso3": "SVK", "name_ru": "Словакия", "name_en": "Slovakia", "name_uk": "Словаччина", "flag": "🇸🇰", "aliases": ["словакия", "slovakia", "словаччина"]},
    {"code": "SI", "iso3": "SVN", "name_ru": "Словения", "name_en": "Slovenia", "name_uk": "Словенія", "flag": "🇸🇮", "aliases": ["словения", "slovenia", "словенія"]},
    {"code": "SB", "iso3": "SLB", "name_ru": "Соломоновы Острова", "name_en": "Solomon Islands", "name_uk": "Соломонові Острови", "flag": "🇸🇧", "aliases": ["соломоновы острова", "solomon islands"]},
    {"code": "SO", "iso3": "SOM", "name_ru": "Сомали", "name_en": "Somalia", "name_uk": "Сомалі", "flag": "🇸🇴", "aliases": ["сомали", "somalia"]},
    {"code": "ZA", "iso3": "ZAF", "name_ru": "ЮАР", "name_en": "South Africa", "name_uk": "ПАР", "flag": "🇿🇦", "aliases": ["юар", "южная африка", "south africa", "пар", "південна африка"]},
    {"code": "SS", "iso3": "SSD", "name_ru": "Южный Судан", "name_en": "South Sudan", "name_uk": "Південний Судан", "flag": "🇸🇸", "aliases": ["южный судан", "south sudan"]},
    {"code": "ES", "iso3": "ESP", "name_ru": "Испания", "name_en": "Spain", "name_uk": "Іспанія", "flag": "🇪🇸", "aliases": ["испания", "spain", "іспанія", "es"]},
    {"code": "LK", "iso3": "LKA", "name_ru": "Шри-Ланка", "name_en": "Sri Lanka", "name_uk": "Шрі-Ланка", "flag": "🇱🇰", "aliases": ["шри-ланка", "sri lanka"]},
    {"code": "SD", "iso3": "SDN", "name_ru": "Судан", "name_en": "Sudan", "name_uk": "Судан", "flag": "🇸🇩", "aliases": ["судан", "sudan"]},
    {"code": "SR", "iso3": "SUR", "name_ru": "Суринам", "name_en": "Suriname", "name_uk": "Суринам", "flag": "🇸🇷", "aliases": ["суринам", "suriname"]},
    {"code": "SE", "iso3": "SWE", "name_ru": "Швеция", "name_en": "Sweden", "name_uk": "Швеція", "flag": "🇸🇪", "aliases": ["швеция", "sweden", "швеція"]},
    {"code": "CH", "iso3": "CHE", "name_ru": "Швейцария", "name_en": "Switzerland", "name_uk": "Швейцарія", "flag": "🇨🇭", "aliases": ["швейцария", "switzerland", "швейцарія"]},
    {"code": "SY", "iso3": "SYR", "name_ru": "Сирия", "name_en": "Syria", "name_uk": "Сирія", "flag": "🇸🇾", "aliases": ["сирия", "syria", "сирія"]},
    {"code": "TW", "iso3": "TWN", "name_ru": "Тайвань", "name_en": "Taiwan", "name_uk": "Тайвань", "flag": "🇹🇼", "aliases": ["тайвань", "taiwan"]},
    {"code": "TJ", "iso3": "TJK", "name_ru": "Таджикистан", "name_en": "Tajikistan", "name_uk": "Таджикистан", "flag": "🇹🇯", "aliases": ["таджикистан", "tajikistan"]},
    {"code": "TZ", "iso3": "TZA", "name_ru": "Танзания", "name_en": "Tanzania", "name_uk": "Танзанія", "flag": "🇹🇿", "aliases": ["танзания", "tanzania", "танзанія"]},
    {"code": "TH", "iso3": "THA", "name_ru": "Таиланд", "name_en": "Thailand", "name_uk": "Таїланд", "flag": "🇹🇭", "aliases": ["таиланд", "thailand", "таїланд"]},
    {"code": "TL", "iso3": "TLS", "name_ru": "Тимор-Лешти", "name_en": "Timor-Leste", "name_uk": "Тимор-Лешті", "flag": "🇹🇱", "aliases": ["тимор", "timor"]},
    {"code": "TG", "iso3": "TGO", "name_ru": "Того", "name_en": "Togo", "name_uk": "Того", "flag": "🇹🇬", "aliases": ["того", "togo"]},
    {"code": "TO", "iso3": "TON", "name_ru": "Тонга", "name_en": "Tonga", "name_uk": "Тонга", "flag": "🇹🇴", "aliases": ["тонга", "tonga"]},
    {"code": "TT", "iso3": "TTO", "name_ru": "Тринидад и Тобаго", "name_en": "Trinidad and Tobago", "name_uk": "Тринідад і Тобаго", "flag": "🇹🇹", "aliases": ["тринидад", "trinidad"]},
    {"code": "TN", "iso3": "TUN", "name_ru": "Тунис", "name_en": "Tunisia", "name_uk": "Туніс", "flag": "🇹🇳", "aliases": ["тунис", "tunisia", "туніс"]},
    {"code": "TR", "iso3": "TUR", "name_ru": "Турция", "name_en": "Turkey", "name_uk": "Туреччина", "flag": "🇹🇷", "aliases": ["турция", "turkey", "туреччина", "tr"]},
    {"code": "TM", "iso3": "TKM", "name_ru": "Туркменистан", "name_en": "Turkmenistan", "name_uk": "Туркменістан", "flag": "🇹🇲", "aliases": ["туркменистан", "turkmenistan"]},
    {"code": "TV", "iso3": "TUV", "name_ru": "Тувалу", "name_en": "Tuvalu", "name_uk": "Тувалу", "flag": "🇹🇻", "aliases": ["тувалу", "tuvalu"]},
    {"code": "UG", "iso3": "UGA", "name_ru": "Уганда", "name_en": "Uganda", "name_uk": "Уганда", "flag": "🇺🇬", "aliases": ["уганда", "uganda", "уґанда", "ug", "uga"]},
    {"code": "UA", "iso3": "UKR", "name_ru": "Украина", "name_en": "Ukraine", "name_uk": "Україна", "flag": "🇺🇦", "aliases": ["украина", "ukraine", "україна", "ukraina", "ua", "ukr"]},
    {"code": "AE", "iso3": "ARE", "name_ru": "ОАЭ", "name_en": "United Arab Emirates", "name_uk": "ОАЕ", "flag": "🇦🇪", "aliases": ["оаэ", "оае", "эмираты", "uae", "united arab emirates"]},
    {"code": "GB", "iso3": "GBR", "name_ru": "Великобритания", "name_en": "United Kingdom", "name_uk": "Велика Британія", "flag": "🇬🇧", "aliases": ["великобритания", "united kingdom", "велика британія", "uk", "gb", "britain", "англия", "england"]},
    {"code": "US", "iso3": "USA", "name_ru": "США", "name_en": "United States", "name_uk": "США", "flag": "🇺🇸", "aliases": ["сша", "usa", "сша", "united states", "america", "америка", "us"]},
    {"code": "UY", "iso3": "URY", "name_ru": "Уругвай", "name_en": "Uruguay", "name_uk": "Уругвай", "flag": "🇺🇾", "aliases": ["уругвай", "uruguay"]},
    {"code": "UZ", "iso3": "UZB", "name_ru": "Узбекистан", "name_en": "Uzbekistan", "name_uk": "Узбекистан", "flag": "🇺🇿", "aliases": ["узбекистан", "uzbekistan", "uz"]},
    {"code": "VU", "iso3": "VUT", "name_ru": "Вануату", "name_en": "Vanuatu", "name_uk": "Вануату", "flag": "🇻🇺", "aliases": ["вануату", "vanuatu"]},
    {"code": "VA", "iso3": "VAT", "name_ru": "Ватикан", "name_en": "Vatican", "name_uk": "Ватикан", "flag": "🇻🇦", "aliases": ["ватикан", "vatican"]},
    {"code": "VE", "iso3": "VEN", "name_ru": "Венесуэла", "name_en": "Venezuela", "name_uk": "Венесуела", "flag": "🇻🇪", "aliases": ["венесуэла", "venezuela"]},
    {"code": "VN", "iso3": "VNM", "name_ru": "Вьетнам", "name_en": "Vietnam", "name_uk": "Вʼєтнам", "flag": "🇻🇳", "aliases": ["вьетнам", "vietnam", "вʼєтнам"]},
    {"code": "YE", "iso3": "YEM", "name_ru": "Йемен", "name_en": "Yemen", "name_uk": "Ємен", "flag": "🇾🇪", "aliases": ["йемен", "yemen", "ємен"]},
    {"code": "ZM", "iso3": "ZMB", "name_ru": "Замбия", "name_en": "Zambia", "name_uk": "Замбія", "flag": "🇿🇲", "aliases": ["замбия", "zambia"]},
    {"code": "ZW", "iso3": "ZWE", "name_ru": "Зимбабве", "name_en": "Zimbabwe", "name_uk": "Зімбабве", "flag": "🇿🇼", "aliases": ["зимбабве", "zimbabwe"]},
]

# Для быстрого поиска — индекс по коду
_BY_CODE = {c["code"]: c for c in COUNTRIES}
_BY_NAME_RU = {c["name_ru"].lower(): c for c in COUNTRIES}

def get_country(code: str):
    return _BY_CODE.get(code.upper())

def get_country_by_name(name: str, lang: str = "ru"):
    """Найти страну по точному названию."""
    low = (name or "").strip().lower()
    for c in COUNTRIES:
        if low in (c["name_ru"].lower(), c["name_en"].lower(), c["name_uk"].lower(), c["code"].lower(), c.get("iso3","").lower()):
            return c
        if low in [a.lower() for a in c.get("aliases", [])]:
            return c
    return None

def is_valid_country(value: str) -> bool:
    if not value:
        return False
    low = value.strip().lower()
    if low in ("all", "все страны", "всі країни", "not_specified", "не указана", "не вказано", "—", "-"):
        return True
    return get_country_by_name(value) is not None

def search_countries(query: str, lang: str = "ru", limit: int = 10) -> List[Dict]:
    """
    Поиск с учётом вариантов написания, регистра и распространённых названий.
    Приоритет: exact match > prefix > contains > alias contains.
    Корректно различает похожие названия: Украина vs Уганда.
    """
    q = (query or "").strip().lower()
    if not q:
        # топ популярных + ALL/NOT_SPECIFIED
        return SPECIAL_OPTIONS + COUNTRIES[:8]

    scored = []
    for c in COUNTRIES:
        names = [c["name_ru"].lower(), c["name_en"].lower(), c["name_uk"].lower(), c["code"].lower(), c.get("iso3","").lower()]
        aliases = [a.lower() for a in c.get("aliases", [])]
        score = 0
        # exact
        if q in names:
            score = 100
        elif any(n == q for n in aliases):
            score = 95
        elif any(n.startswith(q) for n in names):
            score = 80
        elif any(a.startswith(q) for a in aliases):
            score = 75
        elif any(q in n for n in names):
            score = 50
        elif any(q in a for a in aliases):
            score = 45
        else:
            continue
        # бонус для точного различения: если q короткое, предпочитаем prefix а не contains
        # длина страны тоже влияет — короткие названия не должны всплывать случайно
        if score:
            scored.append((score, c))

    # сортировка по score desc, затем по ru имени
    scored.sort(key=lambda x: (-x[0], x[1]["name_ru"]))
    result = [c for score, c in scored[:limit]]
    # если нет результата — предложить спец опции если подходит
    if not result:
        for s in SPECIAL_OPTIONS:
            if q in s["name_ru"].lower() or q in s["name_en"].lower():
                result.append(s)
    return result

def format_country(c: Dict, lang: str = "ru") -> str:
    name = c.get(f"name_{lang}", c["name_ru"])
    return f"{c['flag']} {name} ({c['code']})"

def all_countries():
    return SPECIAL_OPTIONS + COUNTRIES
