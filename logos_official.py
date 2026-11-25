"""Official logos for the companies with the most open jobs (25 Nov 2026; the owner asked three times for real logos instead of the
letter squares: 2,196 of 25,209 companies had one, about 9% of the open jobs).

For each company, most open jobs first, without a logo yet:
  1. its own website: the one in logos.json, the hand-checked one in SITES below, the one its own job board links to (the board we
     read its jobs from), or <name>.com when that is unambiguous (the site names the company in its title and either links to our
     board or the name is a long, non-dictionary one). Never another company's site, never a guess from a short or generic name.
  2. the square icon that site publishes: apple-touch-icon, the icons in its web manifest, <link rel=icon> with sizes, or a
     favicon.ico with a 64 px or larger image. Never an SVG drawn by us, a generated picture or a builder's default icon.
  3. otherwise the square logo the company uploaded to its own job board (Workable, Breezy, JazzHR, Pinpoint, BambooHR).
Checks: at least 60 px, square, not blank, not an enlarged tiny favicon, not a website builder's or hiring system's default.
Saved as assets/logos/<slug>.png (96 px) and assets/logos/s/<slug>.png (72 px), both quantized to a palette, about 2 to 5 KB.

Polite: 4 companies at a time, one request at a time for each, 10 s timeouts, a User-Agent naming the site, and a site that answers
with a bot check (403, 429, 503, a challenge page) is left alone. Progress is kept in data/logos_official.jsonl, so a run can stop
and go on. Usage: python3 logos_official.py [how many companies, default 3000]
"""
import hashlib, html as H, io, json, os, re, subprocess, sys, threading, time, concurrent.futures as cf
from pathlib import Path
from urllib.parse import urljoin, urlparse
from collect import slugify

ROOT = Path(__file__).parent
OUT = ROOT / "assets" / "logos"
MAP = ROOT / "logos.json"
LOG = ROOT / "data" / "logos_official.jsonl"
UA = "Mozilla/5.0 (compatible; JobsEveryHourBot/1.0; +https://jobseveryhour.com/about/)"
FULL = "https://jobseveryhour.com"
WORDS = {w.strip().lower() for w in open("/usr/share/dict/words")} if Path("/usr/share/dict/words").exists() else set()

# Hand-checked sites of companies whose name alone does not lead to them (federal agencies, universities, health systems, brands
# whose site differs from the name). Each was looked up and its home page names the company.
SITES = {
    "Department of Veterans Affairs": "va.gov", "Department of the Army": "army.mil", "Department of the Air Force": "af.mil",
    "Department of the Navy": "navy.mil", "Department of Defense": "defense.gov", "Department of Homeland Security": "dhs.gov",
    "Department of Justice": "justice.gov", "Department of the Interior": "doi.gov", "State of Georgia": "georgia.gov", "State of Oklahoma": "oklahoma.gov",
    "Capco": "capco.com", "Abercrombie & Fitch": "abercrombie.com", "University of Miami": "miami.edu", "Teleperformance": "tp.com", "TD Bank": "tdbank.com",
    "Rochester Regional Health": "rochesterregional.org", "University of Rochester": "rochester.edu", "Veterinary Emergency Group (VEG)": "veg.com",
    "KBR": "kbr.com", "Micron Technology": "micron.com", "Mondelez International": "mondelezinternational.com", "Papa John's": "papajohns.com",
    "UMass Memorial Health": "ummhealth.org", "Dave & Buster’s": "daveandbusters.com", "Ohio State University": "osu.edu", "ASM Global": "asmglobal.com",
    "Lehigh Valley Health Network": "lvhn.org", "J.Crew": "jcrew.com", "PNC": "pnc.com", "Beth Israel Lahey Health": "bilh.org", "Lithia & Driveway": "lithia.com",
    "Cushman & Wakefield": "cushmanwakefield.com", "KLA": "kla.com", "Jabil": "jabil.com", "Johnson & Johnson": "jnj.com", "Jefferson Health": "jeffersonhealth.org",
    "Visa": "visa.com", "RTX": "rtx.com", "KnitWell Group": "knitwellgroup.com", "Veeva": "veeva.com", "Centria Autism": "centriaautism.com",
    "Levi Strauss & Co.": "levistrauss.com", "Motorola Solutions": "motorolasolutions.com", "Vanderbilt University Medical Center": "vumc.org",
    "Essentia Health": "essentiahealth.org", "Intel": "intel.com", "Cisco": "cisco.com", "Academy Sports + Outdoors": "academy.com", "Analog Devices": "analog.com",
    "VF Corporation": "vfc.com", "PUMA": "puma.com", "Memorial Healthcare System": "mhs.net", "Memorial Hermann Health System": "memorialhermann.org",
    "Bristol Myers Squibb": "bms.com", "University of Southern California": "usc.edu", "Nexstar Media Group": "nexstar.tv", "Washington University in St. Louis": "wustl.edu",
    "Fidelity Investments": "fidelity.com", "General Motors": "gm.com", "The University of Texas at Austin": "utexas.edu", "LKQ Corporation": "lkqcorp.com",
    "GlobalFoundries": "gf.com", "Goodwill of Central & Northern Arizona": "goodwillaz.org", "Teledyne FLIR": "flir.com", "DPR Construction": "dpr.com",
    "FeverUp": "feverup.com", "University of Arkansas System": "uasys.edu", "Albany Med Health System": "albanymed.org", "Methodist Le Bonheur Healthcare": "methodisthealth.org",
    "Oshkosh Corporation": "oshkoshcorp.com", "GSK": "gsk.com", "DXC Technology": "dxc.com", "Ivy Tech": "ivytech.edu", "Hospital Sisters Health System": "hshs.org",
    "Northeastern University": "northeastern.edu", "PAM Health": "pamhealth.com", "Dartmouth-Hitchcock Health": "dartmouth-health.org", "Essen Medical Associates": "essenmed.com",
    "VCU Health": "vcuhealth.org", "Gundersen Health System": "gundersenhealth.org", "Enhabit Home Health & Hospice": "ehab.com", "Procter & Gamble": "pg.com",
    "Appalachian Regional Healthcare": "arh.org", "Luminis Health": "luminishealth.org", "AeroVironment": "avinc.com", "Westwood Professional Services": "westwoodps.com",
    "DoorDash USA": "doordash.com", "City Wide Facility Solutions": "gocitywide.com", "Concord Hospital": "concordhospital.org", "Universities of Wisconsin": "wisconsin.edu",
    "Horace Mann - Agent Opportunities": "horacemann.com", "Niagara Bottling": "niagarawater.com", "Uline": "uline.com", "Medical College of Wisconsin": "mcw.edu",
    "University of Chicago": "uchicago.edu", "Morgan & Morgan, P.A.": "forthepeople.com", "Nidec": "nidec.com", "Services For The Underserved": "sus.org",
    "Gilbane Building": "gilbaneco.com", "Lineage": "onelineage.com", "Smyrna Ready Mix": "smyrnareadymix.com", "FedEx Express": "fedex.com",
    "Wake County Public School System": "wcpss.net", "Louisiana State University": "lsu.edu", "Vinfen": "vinfen.org", "Kettering Health": "ketteringhealth.org",
    "Devereux": "devereux.org", "ICF": "icf.com", "Brunswick": "brunswick.com", "Huntsville Hospital Health System": "huntsvillehospital.org",
    "Avis Budget Group": "avisbudgetgroup.com", "Wellpath": "wellpathcare.com", "Southcoast Health System": "southcoast.org", "Vanguard": "vanguard.com",
    "Denver Health": "denverhealth.org", "ITW": "itw.com", "University of Arkansas for Medical Sciences": "uams.edu", "Cadence Academy Preschool": "cadence-education.com",
    "American Axle & Manufacturing": "aam.com", "Roto-Rooter Services": "rotorooter.com", "LPL Financial": "lpl.com", "Sisk": "sisk.com", "Coupa Software": "coupa.com",
    "HP": "hp.com", "3M": "3m.com", "Dane Street, LLC": "danestreet.com", "International Schools Partnership": "internationalschoolspartnership.com",
    "Universal Logistics Holdings": "universallogistics.com", "Princess Cruises": "princess.com",
    "FOX": "foxcorporation.com", "Clearwater Analytics": "clearwateranalytics.com", "CCB iHeartMedia + Entertainment, Inc. | MPG": "iheartmedia.com",
    "F.N.B": "fnb-online.com", "Huron": "huronconsultinggroup.com", "BJ’s Wholesale Club": "bjs.com", "Palm Beach State College": "palmbeachstate.edu",
    "Adobe": "adobe.com", "University of New Hampshire": "unh.edu", "Department of Health and Human Services": "hhs.gov", "State of Maine": "maine.gov",
    "University of Ottawa": "uottawa.ca", "Acts Retirement-Life Communities": "actslife.org", "DICK'S Sporting Goods": "dickssportinggoods.com",
    "Green Thumb": "gtigrows.com", "Young Life": "younglife.org", "State of Oregon": "oregon.gov", "University of Maryland College Park": "umd.edu",
    "ZOLL Medical": "zoll.com", "Wipfli Advisory": "wipfli.com", "ZEISS": "zeiss.com", "Oregon State University": "oregonstate.edu",
    "Republic Services": "republicservices.com", "IKO": "iko.com", "Boston Pizza": "bostonpizza.com", "Hanger": "hanger.com", "Brown & Brown": "bbrown.com",
    "Wright Tree Service": "wrighttree.com", "Advocates": "advocates.org", "B&Q": "diy.com", "Canon U.S.A": "usa.canon.com", "Integer": "integer.net",
    "St. Luke's Hospital": "stlukes-stl.com", "The Hartford": "thehartford.com",
    "Geisinger": "geisinger.org", "The N2 Company": "n2co.com", "Ares Operations": "aresmgmt.com", "C&S Wholesale Grocers": "cswg.com",
    "Ingram Micro": "ingrammicro.com", "Conagra Brands": "conagrabrands.com", "Snap-on": "snapon.com", "American Electric Power": "aep.com",
    "Scout Motors": "scoutmotors.com", "LaBella Associates": "labellapc.com", "CarePoint Health": "carepointhealth.org", "New Balance": "newbalance.com",
    "Cardinal Health": "cardinalhealth.com", "Natera": "natera.com", "HCSC": "hcsc.com", "Impulse Space": "impulsespace.com", "TJX": "tjx.com",
    "First American’s": "firstam.com", "KCI Technologies": "kci.com", "PlayStation Global": "playstation.com", "TransUnion": "transunion.com",
    "Columbia Sportswear": "columbia.com", "Wayne-Sanderson Farms": "waynesandersonfarms.com", "Maintainx": "getmaintainx.com",
    "ACH Arkansas Children's Hospital": "archildrens.org", "Formenergy": "formenergy.com", "Guidepost Montessori": "guidepostmontessori.com",
    "Fanatics Commerce": "fanaticsinc.com", "Axiom Talent Platform": "axiomlaw.com", "Department of Transportation": "transportation.gov", "SSOE": "ssoe.com",
    "Qube Research & Technologies": "qube-rt.com", "First Student": "firststudentinc.com", "McGill University": "mcgill.ca", "GEICO": "geico.com",
    "Paramount Residential Mortgage": "prmg.net", "Hy-Vee": "hy-vee.com", "Acrisure": "acrisure.com", "GCU": "gcu.edu", "Collectors Universe": "collectors.com",
    "Tether": "tether.io", "Pennylane": "pennylane.com", "Keywords Studios": "keywordsstudios.com", "Keller Williams": "kw.com", "Reiss": "reiss.com",
    "Dentsu Creative": "dentsucreative.com", "YMCA of Greater Boston": "ymcaboston.org", "Tavistock Restaurant Collection": "tavistockrestaurants.com",
    "USAA": "usaa.com", "Trend Micro": "trendmicro.com", "Lennar": "lennar.com", "Genesys": "genesys.com", "Geosyntec Consultants": "geosyntec.com",
    "Cook Children's": "cookchildrens.org", "Altera": "altera.com", "Julius Baer": "juliusbaer.com", "Torch Technologies": "torchtechnologies.com",
    "Cooper Norcross University Hospital": "cooperhealth.org", "Presbyterian Homes & Services": "preshomes.org", "VHC Health": "vhchealth.org",
    "Tradesmen International": "tradesmeninternational.com", "Mercy Medical Center": "mercycare.org", "Residential Home Health and Hospice": "residentialhomehealth.com",
    "Ridley's Family Markets": "shopridleys.com", "Bancroft": "bancroft.org", "American House Senior Living Communities": "americanhouse.com", "GRVTY": "grvty.com",
    "Halkey-Roberts": "halkeyroberts.com", "CAMBA": "camba.org", "ZOLL LifeVest": "zoll.com", "Methodist Hospitals": "methodisthospitals.org",
    "Cornell University": "cornell.edu",
    "Lennox International": "lennox.com",
    "Arch Insurance": "archgroup.com",
    "Dow Jones": "dowjones.com",
    "The Coca-Cola Company": "coca-colacompany.com",
    "Utah State University": "usu.edu",
    "University of Pikeville": "upike.edu",
    "Vetcor": "vetcor.com",
    "AdaptHealth": "adapthealth.com",
    "Centerstone": "centerstone.org",
    "Fred Hutchinson Cancer Center": "fredhutch.org",
    "La-Z-Boy": "la-z-boy.com",
    "New School": "newschool.edu",
    "ZT Group Intl, Inc. dba ZT Systems": "ztsystems.com",
    "Charlotte Tilbury": "charlottetilbury.com",
    "MKS": "mks.com",
    "MKS Instruments": "mks.com",
    "Kurt Geiger": "kurtgeiger.com",
    "Morningstar": "morningstar.com",
    "UMGC": "umgc.edu",
    "Vireo Health": "vireohealth.com",
    "gorjana": "gorjana.com",
    "Varsity Brands": "varsitybrands.com",
    "Mejuri": "mejuri.com",
    "Helsing": "helsing.ai",
    "Great American Insurance": "greatamericaninsurancegroup.com",
    "Astera Labs": "asteralabs.com",
    "Via": "ridewithvia.com",
    "Sutter Health": "sutterhealth.org",
    "Youth Villages": "youthvillages.org",
    "Canadian Solar": "canadiansolar.com",
    "United Rentals": "unitedrentals.com",
    "Transamerica": "transamerica.com",
    "General Dynamics Electric Boat": "gdeb.com",
    "Hillsborough College": "hccfl.edu",
    "Jensen Hughes": "jensenhughes.com",
    "Ebury": "ebury.com",
    "Pollo Operations": "pollotropical.com",
    "Ingredion": "ingredion.com",
    "Invenergy": "invenergy.com",
    "Monster Energy": "monsterenergy.com",
    "UMB": "umb.com",
    "Apex Companies": "apexcos.com",
    "Overlake Medical Center": "overlakehospital.org",
    "Frost Bank": "frostbank.com",
    "AlphaSense": "alpha-sense.com",
    "Illumina": "illumina.com",
    "PRU": "prudential.com",
    "inDrive": "indrive.com",
    "Consor Engineers": "consoreng.com",
    "Cohesity": "cohesity.com",
    "Viavi Solutions": "viavisolutions.com",
    "Framatome North America": "framatome.com",
    "Hines": "hines.com",
    "Cable One": "cableone.net",
    "C6 Bank": "c6bank.com.br",
    "Think Together": "thinktogether.org",
    "VST": "vistracorp.com",
    "Vantage Data Centers Management": "vantage-dc.com",
    "Appian Corporation": "appian.com",
    "Boys Town": "boystown.org",
    "Integrity Marketing": "integritymarketing.com",
    "Nasdaq": "nasdaq.com",
    "Cumming": "cumming-group.com",
    "LanguageLine": "languageline.com",
    "Ken Garff": "kengarff.com",
    "VHB": "vhb.com",
    "Waters": "waters.com",
    "Howard University": "howard.edu",
    "Fisher Investments": "fisherinvestments.com",
    "Ccg Ccg": "capitalgroup.com",
    "Lurie Children’s Hospital": "luriechildrens.org",
    "Ciena": "ciena.com",
    "Stifel": "stifel.com",
    "DiDi Global": "didiglobal.com",
    "NCR Voyix": "ncrvoyix.com",
    "Tempus": "tempus.com",
    "European Dynamics": "eurodyn.com",
    "Department of Energy": "energy.gov",
    "Wieland": "wieland.com",
    "Johnson Brothers": "johnsonbrothers.com",
    "Owensboro Health": "owensborohealth.org",
    "C.H. Robinson": "chrobinson.com",
    "Infobip": "infobip.com",
    "AmTrust Financial Services": "amtrustfinancial.com",
    "DLA Piper": "dlapiper.com",
    "Joby Aviation": "jobyaviation.com",
    "L'Occitane En Provence": "loccitane.com",
    "Bohler": "bohlerengineering.com",
    "The Tatitlek": "tatitlek.com",
    "Lush Handmade Cosmetics": "lush.com",
    "Department of Agriculture": "usda.gov",
    "Reformation": "thereformation.com",
    "Hickory Farms": "hickoryfarms.com",
    "Intact Financial": "intactfc.com",
    "Quince": "quince.com",
    "Heywood Hospital": "heywood.org",
    "Nationwide": "nationwide.com",
    "Precision Medicine Group": "precisionmedicinegrp.com",
    "WinCo Foods": "wincofoods.com",
    "Centric Brands": "centricbrands.com",
    "NationsBenefits": "nationsbenefits.com",
    "Isar Aerospace SE": "isaraerospace.com",
    "Control Risks": "controlrisks.com",
    "Associated Bank": "associatedbank.com",
    "PRIDE Industries": "prideindustries.com",
    "Praxis Precision Medicines": "praxismedicines.com",
    "Novanta": "novanta.com",
    "Warner Bros": "warnerbros.com",
    "Brooks Automation": "brooks.com",
    "BronxCare Health System": "bronxcare.org",
    "Benefis": "benefis.org",
    "Silverado": "silverado.com",
    "JustMarkets": "justmarkets.com",
    "Brookfield Real Estate": "brookfieldproperties.com",
    "Infosys Singapore & Australia": "infosys.com",
    "Infosys Consulting - Europe": "infosys.com",
    "Feldman Automotive": "feldmanautomotive.com",
    "Bert Ogden Auto": "bertogden.com",
    "Swickard Auto": "swickard.com",
    "Holman Retail": "holman.com",
    "Bayfront Health": "bayfronthealth.com",
    "Vistry": "vistrygroup.co.uk",
    "Manatee Memorial Hospital": "manateememorial.com",
    "Friendship Public Charter School": "friendshipschools.org",
    "Primrose Retirement Communities": "primroseretirement.com",
    "Aptive": "aptiveresources.com",
    "Health Connect America": "healthconnectamerica.com",
    "Costa Navarino": "costanavarino.com",
    "Iredell Memorial Hospital": "iredellhealth.org",
    "AIT Worldwide Home Delivery": "aitworldwide.com",
    "Island Hospitality Management": "islandhospitality.com",
    "ADAPT Community Network": "adaptcommunitynetwork.org",
    "Archdiocese of San Antonio": "archsa.org",
    "Otterbein SeniorLife": "otterbein.org",
    "Suncrest Hospice": "suncrestcare.com",
    "Armstrong Fluid Technology": "armstrongfluidtechnology.com",
    "Innovetive Petcare": "innovetivepetcare.com",
    "Sares Regis Operating": "sares-regis.com",
    "Triple-S Steel": "sss-steel.com",
    "Road Ranger": "roadrangerusa.com",
    "PopStroke": "popstroke.com",
    "AES": "aes.com",
    "CSL": "csl.com",
    "Blackstone": "blackstone.com",
    "DriveTime Family": "drivetime.com",
    "Aviagen": "aviagen.com",
    "United Community Bank": "ucbi.com",
    "LifeStance Health": "lifestance.com",
    "Thinkbrg.com": "thinkbrg.com",
    "Barr": "barr.com",
    "Remitly": "remitly.com",
    "Zentiva": "zentiva.com",
    "Zendesk": "zendesk.com",
    "M&G Global Services": "mandg.com",
    "Morgan Advanced Materials": "morganadvancedmaterials.com",
    "Baldwin": "baldwin.com",
    "AIT Worldwide Logistics": "aitworldwide.com",
    "Assurant Services Argentina": "assurant.com",
    "Wellington Management": "wellington.com",
    "TRUMPF": "trumpf.com",
    "East Penn Manufacturing Company": "eastpennmanufacturing.com",
    "Mariner Finance": "marinerfinance.com",
    "Kimberly-Clark": "kimberly-clark.com",
    "CHA Consulting": "chacompanies.com",
    "CLEAResult": "clearesult.com",
    "Hogan Lovells Cadwalader": "hoganlovells.com",
    "YMCA of San Diego County": "ymcasd.org",
    "Zoetis": "zoetis.com",
    "HNTB": "hntb.com",
    "CVS Health": "cvshealth.com",
    "Ochsner Health": "ochsner.org",
    "Walter P Moore": "walterpmoore.com",
    "University Hospital, Newark NJ": "uhnj.org",
    "The New York Foundling": "nyfoundling.org",
    "Emerus": "emerus.com",
    "Endeavor Schools": "endeavorschools.com",
    "Flanigan's Enterprises": "flanigans.net",
    "ARS-Rescue Rooter": "ars.com",
    "Sage Hospitality": "sagehospitality.com",
    "Legacy Health": "legacyhealth.org",
    "FutureCare": "futurecare.com",
    "University of Utah Health": "healthcare.utah.edu",
    "Versiti": "versiti.org",
    "EMCOR Government Services": "emcorgroup.com",
    "Shermco Industries": "shermco.com",
    "Liberty Mutual": "libertymutual.com",
    "Steel Dynamics": "steeldynamics.com",
    "MillerKnoll": "millerknoll.com",
    "Markel": "markel.com",
    "Kisco Senior Living": "kiscoseniorliving.com",
    "Pima County": "pima.gov",
    "Grant Thornton": "grantthornton.co.uk",
    "Georgetown": "georgetown.edu",
    "George's Processing": "georgesinc.com",
    "LMU": "lmu.edu",
    "Qiagen": "qiagen.com",
    "Williams": "williams.com",
    "Embry-Riddle": "erau.edu",
    "By Light Professional IT Services": "bylight.com",
    "Western & Southern Financial": "westernsouthern.com",
    "Family Health Centers of San Diego": "fhcsd.org",
    "University Medical Center": "umchealthsystem.com",
    "American Vision Partners": "americanvisionpartners.com",
    "Ring Power": "ringpower.com",
    "Omnissa": "omnissa.com",
    "Mizuho": "mizuhogroup.com",
    "ULSA University of Louisville": "louisville.edu",
    "Mayor and City Council of Baltimore": "baltimorecity.gov",
    "Arcwood Environmental": "arcwoodenviro.com",
    "American Structurepoint": "structurepoint.com",
    "QVC": "qvc.com",
    "University of Waterloo": "uwaterloo.ca",
    "Fractal": "fractal.ai",
    "Interstate Waste Services": "interstatewaste.com",
    "Graham Packaging": "grahampackaging.com",
    "Proofpoint": "proofpoint.com",
    "Milton CAT": "miltoncat.com",
    "Richland County": "richlandcountysc.gov",
    "Carollo Engineers": "carollo.com",
    "Brookdale Community College": "brookdalecc.edu",
    "Xcel Energy": "xcelenergy.com",
    "Children's Mercy KC": "childrensmercy.org",
    "Keller North America": "keller-na.com",
    "University of Massachusetts Medical School": "umassmed.edu",
    "MSA Professional Services": "msa-ps.com",
    "Six Flags Entertainment": "sixflags.com",
    "MPC": "marathonpetroleum.com",
    "NASCAR Employees Please": "nascar.com",
    "CCSWW": "ccsww.org",
    "SB Clinical Practice Management": "stonybrookmedicine.edu",
    "T. Rowe Price": "troweprice.com",
    "Road Runner Sports": "roadrunnersports.com",
    "Fox Factory": "ridefox.com",
    "Freese and Nichols": "freese.com",
    "Werfen": "werfen.com",
    "Atlassian": "atlassian.com",
    "L.L.Bean": "llbean.com",
    "Wintrust": "wintrust.com",
    "MSU Denver": "msudenver.edu",
    "North American Construction": "nacg.ca",
    "Hexcel": "hexcel.com",
    "Mercer University": "mercer.edu",
    "Kennedy Krieger Institute": "kennedykrieger.org",
    "IRSC": "irsc.edu",
    "iA Private Wealth": "iaprivatewealth.ca",
    "CAA": "caa.com",
    "NCR Atleos": "ncratleos.com",
    "The Container Store": "containerstore.com",
    "San Antonio Regional Hospital": "sarh.org",
    "American Heart Association": "heart.org",
    "ISU": "iastate.edu",
    "Kinaxis": "kinaxis.com",
    "Global Credit Union": "globalcu.org",
    "Auxis": "auxis.com",
    "Centric Software": "centricsoftware.com",
    "Prologis Management": "prologis.com",
    "Connection": "connection.com",
    "Latham & Watkins": "lw.com",
    "Argonne": "anl.gov",
    "East Boston Neighborhood Health Center": "ebnhc.org",
    "UNF": "unf.edu",
    "Altasciences": "altasciences.com",
    "Stord": "stord.com",
    "CentraState Healthcare System": "centrastate.com",
    "Minerals Technologies": "mineralstech.com",
    "TMX": "tmx.com",
    "Lloyds Bank": "lloydsbankinggroup.com",
    "Jackson Lewis": "jacksonlewis.com",
    "PerkinElmer": "perkinelmer.com",
    "AltaPointe Health": "altapointe.org",
    "Arctic Wolf": "arcticwolf.com",
    "Momentive": "momentive.com",
    "Montage Health": "montagehealth.org",
    "Trimac Transportation": "trimac.com",
    "Cundall": "cundall.com",
    "University of New Orleans": "uno.edu",
    "University of Tampa": "ut.edu",
    "Grossmont-Cuyamaca Community College District": "gcccd.edu",
    "Unity Technologies": "unity.com",
    "Social Security Administration": "ssa.gov",
    "Magnera": "magnera.com",
    "Change Grow Live": "changegrowlive.org",
    "YETI Coolers": "yeti.com",
    "Miami University": "miamioh.edu",
    "Casella Waste Systems": "casella.com",
    "Mindpath Health": "mindpath.com",
    "Foundation Building Materials": "fbmsales.com",
    "Altorfer CAT": "altorfer.com",
    "Workiva": "workiva.com",
    "Barnard Construction": "barnard-inc.com",
    "BDO Belgium": "bdo.be",
    "KBI Biopharma": "kbibiopharma.com",
    "Sage Dental": "mysagedental.com",
    "WGI": "wginc.com",
    "Plug Power's": "plugpower.com",
    "American University": "american.edu",
    "Cirrus Aircraft": "cirrusaircraft.com",
    "Johnstone Supply": "johnstonesupply.com",
    "RWS": "rws.com",
    "Crum & Forster": "cfins.com",
    "Arizona College of Nursing": "arizonacollege.edu",
    "Florida Medical Clinic": "floridamedicalclinic.com",
    "Titan America": "titanamerica.com",
    "Novelis Warren Manufacturing Facility": "novelis.com",
    "North American Dental Group": "nadentalgroup.com",
    "Goodwill of Greater Washington": "dcgoodwill.org",
    "Solairus Aviation": "solairusaviation.com",
    "BlueSprig": "bluesprigautism.com",
    "Parts Authority": "partsauthority.com",
    "OmniSource": "omnisource.com",
    "Canon Business Process Services": "cbps.canon.com",
    "Guardian Pharmacy Services": "guardianpharmacy.com",
    "Planned Systems International": "plansys.com",
    "St. John's Riverside Hospital": "riversidehealth.org",
    "S&B Engineers and Constructors": "sbec.com",
    "ERP International": "erpinternational.com",
    "48forty Solutions": "48forty.com",
    "Spicerhaart": "spicerhaart.co.uk",
    "The John Stewart": "jsco.net",
    "Dillon Consulting": "dillon.ca",
    "Dohrn": "dohrn.com",
    "Maxis": "maxis.com.my",
    "Crossroads Treatment Centers": "crossroadstreatmentcenters.com",
    "United Energy Workers Healthcare": "uewhealth.com",
    "Somnia": "somniainc.com",
    "Amyx": "amyx.com",
    "JAS": "jas.com",
    "Electric Power Engineers": "epeconsulting.com",
    "MRO": "mrocorp.com",
    "RoviSys Building Technologies": "rovisys.com",
    "Bose Korea": "bose.com",
    "Johnson Matthey": "matthey.com",
    "ModMed Technologies": "modmed.com",
    "Devoted Health. These": "devoted.com",
    "Guardian Life": "guardianlife.com",
    "AML RightSource": "amlrightsource.com",
    "Northwestern Mutual": "northwesternmutual.com",
    "Owens & Minor Distribution": "owens-minor.com",
    "City of Dallas": "dallascityhall.com",
    "AllianceBernstein": "alliancebernstein.com",
    "Epiq": "epiqglobal.com",
    "Harrods": "harrods.com",
    "ERCOT": "ercot.com",
    "WSFS Bank": "wsfsbank.com",
    "CME": "cmegroup.com",
    "WPI Worcester Polytechnic": "wpi.edu",
    "Blackbaud": "blackbaud.com",
    "Entrust": "entrust.com",
    "UQ": "uq.edu.au",
    "DraftKings": "draftkings.com",
    "Yahoo": "yahooinc.com",
    "Burkert": "burkert.com",
    "WEX": "wexinc.com",
    "FICO": "fico.com",
    "MRI Software Instagram": "mrisoftware.com",
    "City of Arlington": "arlingtontx.gov",
    "Department of the Treasury": "treasury.gov",
    "Lamb Weston": "lambweston.com",
    "OneDigital": "onedigital.com",
    "OxyChem": "oxychem.com",
    "o9 Solutions": "o9solutions.com",
    "Duke Energy Employees Current": "duke-energy.com",
    "Pga Tour": "pgatour.com",
    "Shields Health": "shields.com",
    "Mueller Water Products": "muellerwp.com",
    "Brown": "brown.edu",
    "The Andersons": "andersonsinc.com",
    "U.S. Courts": "uscourts.gov",
    "Austin Community College District": "austincc.edu",
    "Healthfirst": "healthfirst.org",
    "Liberty University": "liberty.edu",
    "Winebow": "winebow.com",
    "XPEL": "xpel.com",
    "Husqvarna": "husqvarnagroup.com",
    "WSU": "wsu.edu",
    "Univision": "televisaunivision.com",
    "UVA": "virginia.edu",
    "City and County of Denver": "denvergov.org",
    "FVTC": "fvtc.edu",
    "Newfold Digital": "newfold.com",
    "Kamehameha Schools Trustees of the Estate of Bernice Pauahi Bishop dba Kamehameha Schools": "ksbe.edu",
    "Lhoist": "lhoist.com",
    "The Jackson Laboratory's": "jax.org",
    "Life Fitness": "lifefitness.com",
    "Horizon Media": "horizonmedia.com",
    "Hastings Direct": "hastingsdirect.com",
    "NREL": "nrel.gov",
    "Relativity ODA": "relativity.com",
    "athenahealth": "athenahealth.com",
    "ISS": "issgovernance.com",
    "Holland & Knight": "hklaw.com",
    "Unum": "unum.com",
    "Piedmont Airlines": "piedmont-airlines.com",
    "Loyola": "luc.edu",
    "Mammoth Mountain Ski Area": "mammothmountain.com",
    "Maple Leaf Sports & Entertainment": "mlse.com",
    "LMH Health": "lmh.org",
    "Kith": "kith.com",
    "Lombard Odier": "lombardodier.com",
    "Cerity Partners": "ceritypartners.com",
    "Western Governors University": "wgu.edu",
    "Snowshoe Mountain": "snowshoemtn.com",
    "Mimecast Services": "mimecast.com",
    "Cbrands": "cbrands.com",
    "Osaic": "osaic.com",
    "The Options Clearing": "theocc.com",
    "Department of Commerce": "commerce.gov",
    "Emery Sapp & Sons": "emerysapp.com",
    "Intapp": "intapp.com",
    "Vermeer": "vermeer.com",
    "insightsoftware": "insightsoftware.com",
    "University of San Francisco": "usfca.edu",
    "Creation Technologies": "creationtech.com",
    "Organon": "organon.com",
    "Wilmington Trust": "wilmingtontrust.com",
    "Cengage": "cengage.com",
    "Stevens Transport": "stevenstransport.com",
    "Neurocrine Biosciences": "neurocrine.com",
    "Nelnet": "nelnet.com",
    "Wonder": "wonder.com",
    "NU National University": "nu.edu",
    "Greene, Tweed & Co.": "gtweed.com",
    "Itron": "itron.com",
    "Lesley": "lesley.edu",
    "Golden Valley Memorial Healthcare": "gvmh.org",
    "Svsu Stands Out": "svsu.edu",
    "Techtronic Industries ELC": "ttigroup.com",
    "WFU": "wfu.edu",
    "Guillevin": "guillevin.com",
    "Trafigura": "trafigura.com",
    "EverCommerce": "evercommerce.com",
    "PATH": "path.org",
    "BDC": "bdc.ca",
    "Invenergy Services": "invenergy.com",
    "WPU The William Paterson University of New Jersey": "wpunj.edu",
    "WMG": "wmg.com",
    "OutSystems": "outsystems.com",
    "GenesisCare": "genesiscare.com",
    "Auroragov.org": "auroragov.org",
    "Holland Hospital": "hollandhospital.org",
    "Credit Acceptance": "creditacceptance.com",
    "Berklee": "berklee.edu",
    "LGT": "lgt.com",
    "Breeze Aviation": "flybreeze.com",
    "Holmes Murphy": "holmesmurphy.com",
    "Morningstar DBRS": "dbrs.morningstar.com",
    "Pillsbury Winthrop Shaw Pittman": "pillsburylaw.com",
    "Florida Atlantic University": "fau.edu",
    "Hunt Electric": "huntelec.com",
    "FINRA": "finra.org",
    "First PREMIER Bank": "firstpremier.com",
    "Wounded Warrior Project": "woundedwarriorproject.org",
    "Cloudera": "cloudera.com",
    "Vertex Inc.": "vertexinc.com",
    "ASPCA": "aspca.org",
    "House of Representatives": "house.gov",
    "Nebraska Medicine": "nebraskamed.com",
    "Blizzard Entertainment": "blizzard.com",
    "Ocean Spray": "oceanspray.com",
    "CGB Enterprises": "cgb.com",
    "William Morris Endeavor Entertainment": "wmeagency.com",
    "Simmons University": "simmons.edu",
    "Audubon Society": "audubon.org",
    "CompoSecure": "composecure.com",
    "WP": "washingtonpost.com",
    "ACRT Services": "acrtinc.com",
    "Lendlease": "lendlease.com",
    "Department of State": "state.gov",
    "HHMI": "hhmi.org",
    "Central Intelligence Agency": "cia.gov",
    "BYU": "byu.edu",
    "Cambium Learning": "cambiumlearning.com",
    "Teladoc Health": "teladochealth.com",
    "Midtown Athletic Clubs": "midtown.com",
    "WASH Multifamily Laundry": "wash.com",
    "Columbia Sportswear Comp": "columbia.com",
    "Collin College": "collin.edu",
    "LGI": "lgihomes.com",
    "World Fuel Services": "world-kinect.com",
    "Datasite": "datasite.com",
    "RBFCU Established": "rbfcu.org",
    "John Lewis Partnership": "johnlewispartnership.co.uk",
    "College Board": "collegeboard.org",
    "Smithsonian Institution": "si.edu",
    "Calvin University": "calvin.edu",
    "VSP Vision": "vspvision.com",
    "Helmerich & Payne Management": "helmerichpayne.com",
    "Fhi 360": "fhi360.org",
    "National Indemnity": "nationalindemnity.com",
    "Steamboat Ski & Resort": "steamboat.com",
    "Wentworth Institute of Technology": "wit.edu",
    "Cityblock Health": "cityblock.com",
    "Green Dot": "greendot.com",
    "Jackson Healthcare": "jacksonhealthcare.com",
    "CCC Intelligent Solutions": "cccis.com",
    "Florida Tech": "fit.edu",
    "Uniphore": "uniphore.com",
    "Union College Officially": "union.edu",
    "Fairfield University": "fairfield.edu",
    "Nebraska Orthopaedic Hospital": "nebraskaorthopaedichospital.com",
    "New York Post": "nypost.com",
    "Taco Mac Restaurant": "tacomac.com",
    "Bailey Nelson": "baileynelson.com.au",
    "Apna": "apna.co",
    "Bethesda Health Group": "bethesdahealth.org",
    "Geeks on Site": "geeksonsite.com",
    "Pearce Services": "pearceservices.com",
    "Industrial Electric Manufacturing": "iemfg.com",
    "Veterinary Practice Partners": "vppartners.com",
    "Consigli Construction": "consigli.com",
    "Flatiron Construction": "flatironcorp.com",
    "Healthpro Heritage": "healthpro-heritage.com",
    "GFT": "gftinc.com",
    "The Salvation Army Eastern Territory": "easternusa.salvationarmy.org",
    "Community Health System": "communitymedical.org",
    "YMCA of Greater Oklahoma City": "ymcaokc.org",
    "South College": "south.edu",
    "Jacent Strategic Merchandising": "jacent.com",
    "WME": "wmeagency.com",
    "Hyster-Yale Materials Handling": "hyster-yale.com",
    "CNM Central New Mexico Community College": "cnm.edu",
    "Chatham Financial": "chathamfinancial.com",
    "Evolent Health": "evolent.com",
    "Endicott College": "endicott.edu",
    "Covetrus": "covetrus.com",
    "APEX Fintech Services": "apexfintechsolutions.com",
    "Associated Electric Cooperative": "aeci.org",
    "Choate Construction": "choateco.com",
    "Manhattan": "manh.com",
    "Blue Mountain Resorts Limited Partnership": "bluemountain.ca",
    "Guggenheim Securities": "guggenheimpartners.com",
    "Canada Pension Plan Investment Board": "cppinvestments.com",
    "Fenwick & West": "fenwick.com",
    "Pasadena Hospital Association, LTD dba Huntington Health": "huntingtonhealth.org",
    "SJC San Juan College": "sanjuancollege.edu",
    "Volaris": "volarisgroup.com",
    "Bernalillo County": "bernco.gov",
    "Roswell Park Comprehensive Cancer": "roswellpark.org",
    "Acxiom": "acxiom.com",
    "Harris Computer": "harriscomputer.com",
    "King & Spalding": "kslaw.com",
    "Bristow": "bristowgroup.com",
    "MICA": "mica.edu",
    "Bentley University": "bentley.edu",
    "GNW": "genworth.com",
    "LendingClub": "lendingclub.com",
    "Modivcare": "modivcare.com",
    "Globe Life": "globelifeinsurance.com",
    "Nueces County": "nuecesco.com",
    "ONU": "onu.edu",
    "Risepoint": "risepoint.com",
    "AMN Healthcare": "amnhealthcare.com",
    "KANTAR Kantar": "kantar.com",
    "CCRC Child Care Resource Center": "ccrcca.org",
    "Underwriters Laboratories": "ul.org",
    "World Economic Forum Geneva": "weforum.org",
    "NiSource": "nisource.com",
    "Multnomah County": "multco.us",
    "Deer Valley Resort": "deervalley.com",
    "BCBST": "bcbst.com",
    "Intrum": "intrum.com",
    "Cerence AI": "cerence.com",
    "Privilege Underwriters": "pureinsurance.com",
    "Jotun": "jotun.com",
    "Sugarbush Mountain Resort": "sugarbush.com",
    "Walker & Dunlop": "walkerdunlop.com",
    "Crystal Mountain": "crystalmountainresort.com",
    "Adams State University": "adams.edu",
    "Oakland County": "oakgov.com",
    "Macquarie University": "mq.edu.au",
    "Toyota Tsusho America": "taiamerica.com",
    "BMC": "bmc.org",
    "Global Partners": "globalp.com",
    "Caliber Collision": "caliber.com",
    "Cedarhurst": "cedarhurstliving.com",
    "Benchmark Resorts": "benchmarkresortsandhotels.com",
    "DUAL North America": "dualgroup.com",
    "Haier": "haier.com",
    "Ubiquiti": "ui.com",
    "Innodata Inc.": "innodata.com",
    "Fashion Nova": "fashionnova.com",
    "Modern Animal": "modernanimal.com",
    "Crisp & Green": "crispandgreen.com",
    "American Income Life": "ailife.com",
    "Simtra BioPharma Solutions": "simtrabps.com",
    "QUI Tequila": "quitequila.com",
    "Big Bowl": "bigbowl.com",
    "Arbor Lodging": "arborlodging.com",
    "QSL Management": "qslmanagement.com",
    "Better Health": "betterhealthgroup.com",
    "Global Pacific Support": "globalpacificsupport.com",
    "The Swift Group": "theswiftgroup.com",
    "J Rose Logistics": "jroselogistics.com",
    "Triple T Hospitality": "triplethospitality.com",
    "Pediatrics Plus": "pediatricsplus.com",
    "Ensemble Hospitality": "ensemblehospitality.com",
    "Children's Home Healthcare": "childrenshomehealthcare.com",
}

ATS_HOSTS = re.compile(r"(greenhouse\.io|greenhouse\.com|lever\.co|ashbyhq\.com|ashbyprd\.com|myworkdayjobs\.com|myworkday\.com|workday\.com|"
                       r"icims\.com|jibeapply\.com|paylocity\.com|bamboohr\.com|breezy\.hr|applytojob\.com|jazzhr\.com|resumator|workable\.com|"
                       r"rippling\.com|ripplingcdn\.com|pinpointhq\.com|gem\.com|recruitee\.com|teamtailor|personio|trakstar\.com|smartrecruiters\.com|"
                       r"usajobs\.gov|talentbrew\.com|radancy|phenom|successfactors|taleo|oraclecloud\.com|ultipro|ukg|adp\.com|dayforce|"
                       r"linkedin\.com|facebook\.com|fb\.com|twitter\.com|x\.com|instagram\.com|youtube\.com|tiktok\.com|glassdoor|indeed\.com|"
                       r"google|gstatic|googleapis|googletagmanager|doubleclick|cloudflare|cloudfront\.net|amazonaws\.com|azureedge\.net|akamai|"
                       r"fastly|jsdelivr|unpkg|w3\.org|ogp\.me|schema\.org|cookielaw|onetrust|cookiebot|hotjar|sentry|rollbar|sumologic|segment|"
                       r"hubspot|hsforms|wix\.com|wixstatic|parastorage|wixapps|wix-code|squarespace|shopify|webflow|website-files|wordpress\.(?:com|org)|"
                       r"wp\.com|gravatar|typekit|fontawesome|adobe\.com|apple\.com|microsoft\.com|mozilla\.org|cloudinary\.com|imgix|b-cdn\.net|"
                       r"sharethis|addthis|zdassets|zendesk|intercom|drift|recaptcha|bing\.com|yahoo|vimeo|wistia|pinterest|enable-javascript)", re.I)
DEFAULT_ICON = re.compile(r"(wp-includes/images/w-logo|wp\.com/i/webclip|wordpress-logo|/wp-admin/|wix\.com/favicon|/universal/default-favicon|"
                          r"website-files\.com/img/(?:favicon|webclip)|webflow\.com/img/(?:favicon|webclip)|/img/webclip\.png|"
                          r"logo-default\.png|isteam/ip/static|weebly\.com/favicon|squarespace\.com/favicon|shopify\.com/favicon|"
                          r"hubspot.*favicon|godaddy|default[-_]?favicon|favicon[-_]default|placeholder|/img/v1\.1/favicons/)", re.I)   # the last: JazzHR's own
CHALLENGE = re.compile(r"(cf-chl|challenge-platform|just a moment\.\.\.|attention required|px-captcha|_incapsula_resource|captcha-delivery|"
                       r"pardon our interruption|access denied|request unsuccessful|are you a robot|bot detection|ddos-guard|sgcaptcha)", re.I)
PARKED = re.compile(r"(domain (?:name )?(?:is )?for sale|buy this domain|this domain may be for sale|hugedomains|sedoparking|parkingcrew|"
                    r"bodis|afternic|dan\.com|domain parking|is parked free)", re.I)
SUFFIX = re.compile(r"\b(inc|llc|l\.l\.c|ltd|limited|corp|corporation|company|co|plc|gmbh|ag|sa|s\.a|bv|nv|pty|pvt|private|lp|llp|pc|pllc|the)\b\.?", re.I)

_lock = threading.Lock()
TRIED = {}                # domain -> (status, final_url, html) of its home page, shared between companies with the same site


def norm(s):
    return re.sub(r"[^a-z0-9]", "", H.unescape(s or "").lower())


def base_name(name, amp=" and "):
    n = re.sub(r"\([^)]*\)", " ", name)
    return norm(SUFFIX.sub(" ", n.replace("&", amp))) or norm(name)


def root_domain(host):
    """careers.acme.com -> acme.com, shop.acme.co.uk -> acme.co.uk"""
    parts = host.split(".")
    keep = 3 if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "net", "gov", "ac", "edu") and len(parts[-1]) == 2 else 2
    return ".".join(parts[-keep:])


def curl(url, binary=False, limit=900_000):
    """(status, final url, content type, body) with the site's User-Agent, 10 s, redirects followed; body cut at `limit` bytes."""
    try:
        r = subprocess.run(["curl", "-s", "-L", "--max-redirs", "6", "--max-time", "10", "--compressed", "-A", UA,
                            "-H", "Accept: text/html,application/xhtml+xml,image/*,*/*;q=0.8", "-H", "Accept-Language: en-US,en;q=0.8",
                            "-w", "%{stderr}%{http_code} %{url_effective} %{content_type}", url], capture_output=True, timeout=14)
        meta = r.stderr.decode("utf-8", "replace").strip().split(" ")
        status = int(meta[0]) if meta and meta[0].isdigit() else 0
        body = r.stdout[:limit]
        return status, (meta[1] if len(meta) > 1 else url), (meta[2].lower() if len(meta) > 2 else ""), body if binary else body.decode("utf-8", "replace")
    except Exception:
        return 0, url, "", b"" if binary else ""


def host_of(url):
    h = (urlparse(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def label_of(host):
    """The registrable name of a host: careers.acme.co.uk -> acme."""
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "net", "gov", "ac", "edu") and len(parts[-1]) == 2: return parts[-3]
    return parts[-2] if len(parts) >= 2 else host


def blocked(status, text):
    """A refusal or a bot check, which is left alone. The word captcha alone counts only on a short page: a whole home page that
    loads Google's reCAPTCHA for its contact form, or a Wix site (its list of modules names "captcha"), is not a check
    (26 Nov 2026: veg.com, fnb-online.com, trilon.com were skipped as blocked)."""
    if status in (0, 401, 403, 405, 406, 409, 429, 451, 503, 520, 521, 522, 523, 525, 526) or CHALLENGE.search(text[:6000]): return True
    return len(text) < 20000 and bool(re.search(r"(?<!re)captcha", text[:6000], re.I))


def home(domain):
    with _lock:
        if domain in TRIED: return TRIED[domain]
    st, final, ctype, text = curl(f"https://{domain}/")
    if (st == 0 or st >= 500) and not domain.startswith("www."):
        st, final, ctype, text = curl(f"https://www.{domain}/")
    got = (st, final, text if "html" in ctype or text.lstrip().startswith("<") else "")
    with _lock: TRIED[domain] = got
    return got


def head_names(text):
    head = text[:200000]
    out = re.findall(r"<title[^>]*>(.*?)</title>", head, re.S | re.I)[:1]
    for prop in ("og:site_name", "application-name", "og:title", "apple-mobile-web-app-title"):
        out += re.findall(r'<meta[^>]+(?:property|name)=["\']' + prop + r'["\'][^>]*content=["\']([^"\']+)', head, re.I)
        out += re.findall(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']' + prop + r'["\']', head, re.I)
    out += re.findall(r'"@type"\s*:\s*"(?:Organization|Corporation|LocalBusiness|NGO|EducationalOrganization|GovernmentOrganization|'
                      r'Hospital|MedicalOrganization|CollegeOrUniversity)"[^{}]{0,400}?"name"\s*:\s*"([^"]+)"', head)
    return norm(" ".join(out))


def board_evidence(src, text):
    """Does the page link to the very job board we read this company's jobs from?"""
    ats, tok = (src.get("ats") or "").lower(), (src.get("token") or "").lower()
    t = text.lower()
    if not tok: return False
    if ats == "workday":
        tenant, _, site = tok.partition("/")
        ten = tenant.split(".")[0]
        return (f"{ten}.wd" in t and "myworkdayjobs" in t) or (bool(site) and f"myworkdayjobs.com/{site.lower()}" in t) or f"myworkdayjobs.com/en-us/{site.lower()}" in t
    pats = {"greenhouse": [f"greenhouse.io/{tok}", f"for={tok}", f"boards/{tok}/"], "lever": [f"lever.co/{tok}"], "ashby": [f"ashbyhq.com/{tok}"],
            "icims": [f"{tok}.icims.com"], "jazzhr": [f"{tok}.applytojob.com"], "bamboohr": [f"{tok}.bamboohr.com"], "breezy": [f"{tok}.breezy.hr"],
            "paylocity": [tok], "workable": [f"workable.com/{tok}"], "rippling": [f"rippling.com/{tok}"], "pinpoint": [f"{tok}.pinpointhq.com"],
            "gem": [f"gem.com/{tok}"], "recruitee": [f"{tok}.recruitee.com"], "teamtailor": [f"{tok}.teamtailor.com", tok if "." in tok else "\0"],
            "personio": [f"{tok}.jobs.personio"], "trakstar": [f"{tok}.hire.trakstar.com"], "smartrecruiters": [f"smartrecruiters.com/{tok}"]}
    return any(p in t for p in pats.get(ats, []))


def tenant_of(src):
    ats, tok = (src.get("ats") or "").lower(), (src.get("token") or "")
    if ats == "workday": return norm(tok.split(".")[0])
    if ats == "icims": return norm(re.sub(r"^(careers|jobs|uscareers|external|careers-us|en-us)-", "", tok.lower()))
    if ats == "paylocity" or re.search(r"-\d+$", tok): return ""
    return norm(re.sub(r"-(inc|llc|ltd|careers|jobs|hr|us|usa)$", "", tok.lower()))


BOARD_PAGE = {"greenhouse": "https://job-boards.greenhouse.io/{t}", "lever": "https://jobs.lever.co/{t}", "ashby": "https://jobs.ashbyhq.com/{t}",
              "jazzhr": "https://{t}.applytojob.com/apply", "breezy": "https://{t}.breezy.hr/", "pinpoint": "https://{t}.pinpointhq.com/",
              "rippling": "https://ats.rippling.com/{t}/jobs", "icims": "https://{t}.icims.com/jobs", "gem": "https://jobs.gem.com/{t}",
              "recruitee": "https://{t}.recruitee.com/", "trakstar": "https://{t}.hire.trakstar.com/", "bamboohr": "https://{t}.bamboohr.com/careers"}


def board_site(src, name):
    """The company's own site as its job board links to it (the board is the company's: it posts the jobs we list)."""
    ats, tok = (src.get("ats") or "").lower(), src.get("token") or ""
    if ats not in BOARD_PAGE or not tok or (ats == "teamtailor"): return None, ""
    st, final, _, text = curl(BOARD_PAGE[ats].format(t=tok))
    if st != 200 or not text: return None, ""
    hosts = {}
    for h in re.findall(r'https?:(?://|\\/\\/|\\u002F\\u002F)([a-z0-9.-]+\.[a-z]{2,})', text, re.I):
        h = h.lower(); h = h[4:] if h.startswith("www.") else h
        if ATS_HOSTS.search(h) or (h == host_of(final) and ATS_HOSTS.search(h or "x")): continue
        hosts[h] = hosts.get(h, 0) + 1
    key, b, ten = norm(name), base_name(name), tenant_of(src)
    acro = "".join(w[0] for w in re.findall(r"[A-Za-z0-9]+", re.sub(r"\([^)]*\)", " ", name)) if w.lower() not in ("of", "and", "the", "for")).lower()
    best = None
    for h, n in sorted(hosts.items(), key=lambda kv: -kv[1]):
        lab = label_of(h)
        if len(lab) < 3: continue
        if lab in key or lab == ten or b.startswith(lab) or (len(b) >= 4 and b in lab) or (len(acro) >= 3 and lab == acro) or (ten and len(ten) >= 4 and ten in lab):
            best = h; break
    return best, text


def name_candidates(name, src):
    b, ten = base_name(name), tenant_of(src)
    out = []
    for stem in (norm(name) if norm(name) != b and len(norm(name)) <= 30 else "", b, ten):
        if stem and len(stem) >= 3: out.append(f"{stem}.com")
    return list(dict.fromkeys(out))


def generic(name):
    words = [w.lower() for w in re.findall(r"[A-Za-z]+", re.sub(r"\([^)]*\)", " ", SUFFIX.sub(" ", name)))]
    return bool(words) and all(w in WORDS for w in words)


# ---------------------------------------------------------------------------------------------------------- the icon of a site
def icon_links(text, page_url):
    cands = []
    head = text[:250000]
    for tag in re.findall(r"<link\b[^>]*>", head, re.I):
        rel = re.search(r'\brel\s*=\s*["\']?([^"\'>]+)', tag, re.I); href = re.search(r'\bhref\s*=\s*["\']?([^"\'\s>]+)', tag, re.I)
        if not rel or not href: continue
        r = rel.group(1).lower()
        if "icon" not in r or "mask" in r: continue
        u = urljoin(page_url, H.unescape(href.group(1)))
        if "/cdn/shop/" in u or "cdn.shopify.com" in u:                # Shopify serves the uploaded icon cut to 32 px: ask for 180
            u = re.sub(r"([?&](?:width|height))=\d+", r"\1=180", u)
        sz = re.search(r'sizes\s*=\s*["\']?(\d+)x(\d+)', tag, re.I)
        n = int(sz.group(1)) if sz else (180 if "apple" in r else 0)
        if u.lower().split("?")[0].endswith(".svg") or "image/svg" in tag.lower(): n = 400        # a vector icon, drawn at 192 px below
        cands.append((("apple" in r) * 1000 + min(n, 512), u))
    m = re.search(r'<link\b[^>]*rel\s*=\s*["\']?manifest[^>]*>', head, re.I)
    if m:
        href = re.search(r'href\s*=\s*["\']?([^"\'\s>]+)', m.group(0), re.I)
        if href:
            mu = urljoin(page_url, H.unescape(href.group(1)))
            st, _, _, mt = curl(mu, limit=200_000)
            try:
                for ic in (json.loads(mt).get("icons") or []) if st == 200 else []:
                    if not isinstance(ic, dict) or "monochrome" in str(ic.get("purpose", "")) or str(ic.get("src", "")).lower().endswith(".svg"): continue
                    sz = re.match(r"(\d+)x(\d+)", str(ic.get("sizes", "")))
                    n = int(sz.group(1)) if sz else 0
                    if n >= 64: cands.append((900 + min(n, 512) - (300 if n > 512 else 0), urljoin(mu, ic["src"])))
            except Exception:
                pass
    # the logo the site declares for its organization in JSON-LD: often a wide word mark (refused below), sometimes a square mark
    for u in re.findall(r'"logo"\s*:\s*(?:\{[^{}]*?"url"\s*:\s*)?"(https?:[^"]+?\.(?:png|jpe?g|webp)(?:\?[^"]*)?)"', head, re.I)[:2]:
        if re.search(r"logo|icon|mark|symbol", u.rsplit("/", 1)[-1], re.I):     # not a photo a theme puts there (Hantz: a slider picture)
            cands.append((60, urljoin(page_url, u.replace("\\/", "/"))))
    for tag in re.findall(r'<meta[^>]+name=["\']msapplication-TileImage["\'][^>]*>', head, re.I):
        c = re.search(r'content=["\']([^"\']+)', tag)
        if c and not c.group(1).lower().endswith(".svg"): cands.append((100, urljoin(page_url, c.group(1))))
    root = f"{urlparse(page_url).scheme}://{urlparse(page_url).netloc}/"
    cands += [(500, root + "apple-touch-icon.png"), (50, root + "favicon.ico")]
    seen, out = set(), []
    for score, u in sorted(cands, key=lambda c: -c[0]):
        if u in seen or DEFAULT_ICON.search(u) or not u.startswith("http"): continue
        seen.add(u); out.append(u)
    return out


TMP = Path(os.environ.get("HRN_LOGO_TMP", "/tmp")) / "hrn_logo_tmp"


QL_SCALE = []          # how many picture pixels Quick Look draws for one SVG pixel (0.64 on this Mac), measured once


def ql_render(data):
    TMP.mkdir(parents=True, exist_ok=True)
    name = hashlib.md5(data).hexdigest()
    src = TMP / f"{name}.svg"; src.write_bytes(data)
    out = TMP / f"{name}.svg.png"
    try:
        subprocess.run(["qlmanage", "-t", "-s", "192", "-o", str(TMP), str(src)], capture_output=True, timeout=20)
        return out.read_bytes() if out.exists() else b""
    finally:
        src.unlink(missing_ok=True); out.unlink(missing_ok=True)


def svg_sized(data):
    """(SVG drawn to fill 192 px, (w, h) of the drawn part). Quick Look draws an SVG at its own width and height, scaled by
    QL_SCALE, in the corner of a 192 px white picture: a favicon.svg that says width="16" came out as a speck in the corner, a
    192 px one as two thirds of the picture (26 Nov 2026: Scout Motors, AdaptHealth, Mejuri). So the root gets the size that fills
    192 px, and the drawn part is cut out afterwards."""
    from PIL import Image, ImageChops
    if not QL_SCALE:
        png = ql_render(b'<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 10 10"><rect width="10" height="10" fill="red"/></svg>')
        try:
            im = Image.open(io.BytesIO(png)).convert("RGB")
            box = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
            QL_SCALE.append(box[2] / 300 if box else 0.64)
        except Exception:
            QL_SCALE.append(0.64)
    text = data.decode("utf-8", "replace")
    m = re.search(r"<svg\b[^>]*>", text, re.I)
    if not m: return data, None
    tag = m.group(0)
    num = lambda a: (re.search(r'\s' + a + r'\s*=\s*["\']\s*([\d.]+)\s*(?:px)?\s*["\']', tag) or [None, None])[1]
    w, h = num("width"), num("height")
    vb = re.search(r'\bviewBox\s*=\s*["\']\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)', tag, re.I)
    if vb: vw, vh = float(vb.group(1)), float(vb.group(2))
    elif w and h:
        vw, vh = float(w), float(h)
        tag = tag[:4] + f' viewBox="0 0 {w} {h}"' + tag[4:]
    else: return data, None
    if vw <= 0 or vh <= 0: return data, None
    side = 192 / QL_SCALE[0]
    tw, th = (side, side * vh / vw) if vw >= vh else (side * vw / vh, side)
    tag = re.sub(r'\s(width|height)\s*=\s*["\'][^"\']*["\']', "", tag)
    tag = tag[:4] + f' width="{tw:.0f}" height="{th:.0f}"' + tag[4:]
    return (text[:m.start()] + tag + text[m.end():]).encode("utf-8"), (round(tw * QL_SCALE[0]), round(th * QL_SCALE[0]))


def converted(data, kind):
    """The picture as PNG bytes through macOS tools: an SVG drawn to fill 192 px by Quick Look (on white), a WebP read by sips."""
    if kind == "svg":
        from PIL import Image
        sized, drawn = svg_sized(data)
        png = ql_render(sized)
        if not png or not drawn: return png
        im = Image.open(io.BytesIO(png)); im.load()
        buf = io.BytesIO(); im.crop((0, 0, min(drawn[0], im.width), min(drawn[1], im.height))).save(buf, "PNG")
        return buf.getvalue()
    TMP.mkdir(parents=True, exist_ok=True)
    name = hashlib.md5(data).hexdigest()
    src = TMP / f"{name}.{kind}"; src.write_bytes(data)
    out = TMP / f"{name}.png"
    try:
        subprocess.run(["sips", "-s", "format", "png", str(src), "--out", str(out)], capture_output=True, timeout=20)
        return out.read_bytes() if out.exists() else b""
    finally:
        src.unlink(missing_ok=True); out.unlink(missing_ok=True)


def load_image(data):
    from PIL import Image
    head = data[:600].lstrip().lower()
    if head.startswith(b"<svg") or (head[:1] == b"<" and b"<svg" in data[:3000].lower() and b"<html" not in data[:3000].lower()):
        data = converted(data, "svg")          # also one that opens with <?xml, a <!DOCTYPE svg or an editor's comment
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP": data = converted(data, "webp")
    elif data[4:12] in (b"ftypavif", b"ftypavis"): data = converted(data, "avif")          # Pillow here has no AVIF; sips reads it
    im = Image.open(io.BytesIO(data))
    if im.format == "ICO":
        sizes = sorted(im.info.get("sizes") or [im.size], key=lambda s: -s[0])
        im.size = sizes[0]
    im.load()
    return im.convert("RGBA")


def good_icon(im, least=48, square=1.15):
    """None when the picture is fit for a 28 to 64 px square, else why not. A favicon.ico needs 64 px, other icons 48; a logo
    uploaded to a job board may be a little off square (up to 1.3, as logos.py takes them) and is centred on a square."""
    from PIL import Image, ImageStat, ImageChops
    w, h = im.size
    if min(w, h) < least: return f"small {w}x{h}"
    if max(w, h) > square * min(w, h): return f"not square {w}x{h}"
    a = im.getchannel("A")
    if ImageStat.Stat(a).mean[0] < 12: return "transparent"
    flat = Image.new("RGBA", im.size, (255, 255, 255, 255)); flat.alpha_composite(im)
    g = flat.convert("L").resize((64, 64), Image.LANCZOS)
    if ImageStat.Stat(g).stddev[0] < 6: return "blank"
    # a small mark in a corner or a thin word mark on a large empty field is unreadable at 28 px (25 Nov 2026: three such)
    rgb = flat.convert("RGB").resize((64, 64), Image.LANCZOS)
    corner = rgb.crop((0, 0, 1, 1)).resize((64, 64))
    if ImageStat.Stat(corner.convert("L")).mean[0] > 235:            # on white (a coloured tile is the logo's own square)
        box = ImageChops.difference(rgb, corner).convert("L").point(lambda v: 255 if v > 40 else 0).getbbox()
        if box and max(box[2] - box[0], box[3] - box[1]) < 32: return "small mark on an empty field"
    for s in (16, 24):           # an enlarged 16 or 24 px favicon: nothing more in it than in its small copy
        back = g.resize((s, s), Image.LANCZOS).resize((64, 64), Image.BICUBIC)
        if ImageStat.Stat(ImageChops.difference(g, back)).mean[0] < 1.6: return f"enlarged from {s}px"
        nn = g.resize((s, s), Image.NEAREST).resize((64, 64), Image.NEAREST)
        if ImageStat.Stat(ImageChops.difference(g, nn)).mean[0] < 0.8: return f"pixelated from {s}px"
    return None


def save_icon(im, slug):
    from PIL import Image
    w, h = im.size
    side = max(w, h)
    sq = Image.new("RGBA", (side, side), (255, 255, 255, 0)); sq.alpha_composite(im, ((side - w) // 2, (side - h) // 2))
    paths = []
    for px, dest in ((96, OUT / f"{slug}.png"), (72, OUT / "s" / f"{slug}.png")):
        small = sq.resize((px, px), Image.LANCZOS)
        best = None
        for colors in (128, 64):
            buf = io.BytesIO()
            small.quantize(colors=colors, method=Image.Quantize.FASTOCTREE).save(buf, "PNG", optimize=True)
            best = buf.getvalue()
            if len(best) <= (5200 if px == 96 else 3800): break
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(best); paths.append(dest)
    return paths


def site_icon(page_url, text):
    """(picture, url, why-not list) of the best icon the site publishes."""
    why = []
    for u in icon_links(text, page_url)[:6]:
        st, final, ctype, data = curl(u, binary=True, limit=2_000_000)
        if st != 200 or len(data) < 200 or "html" in ctype: why.append(f"{st} {u}"); continue
        if DEFAULT_ICON.search(final): why.append(f"default {final}"); continue
        try: im = load_image(data)
        except Exception: why.append(f"unreadable {u}"); continue
        bad = good_icon(im, 64 if data[:4] == b"\x00\x00\x01\x00" or u.lower().split("?")[0].endswith(".ico") else 48)
        if bad: why.append(f"{bad} {u}"); continue
        return im, u, why
    return None, "", why


def board_logo(src, page_text):
    """The square logo the company uploaded to its job board (only boards whose page we already read)."""
    ats = (src.get("ats") or "").lower()
    urls = []
    if ats == "workday" and "/" in (src.get("token") or ""):            # the logo on the company's Workday career site
        tenant, _, site = src["token"].partition("/")
        urls = [f"https://{tenant}.myworkdayjobs.com/{site}/assets/logo"]
    elif ats == "breezy": urls = re.findall(r'<img[^>]+src="(https://gallery-cdn\.breezy\.hr/[^"]+)"', page_text)
    elif ats == "jazzhr": urls = ["https:" + u if u.startswith("//") else u for u in re.findall(r'<img[^>]+src="((?:https:)?//s3\.amazonaws\.com/resumator/[^"]+/logos/[^"]+)"', page_text)]
    elif ats == "pinpoint": urls = re.findall(r'"(https://[^"]+(?:cloudinary|pinpoint-production)[^"]+logo[^"]*\.(?:png|jpg|jpeg|webp))"', page_text, re.I)
    elif ats == "bamboohr": urls = [u.replace("\\/", "/") for u in re.findall(r'"(https:\\?/\\?/images\d*\.bamboohr\.com\\?/\d+\\?/logos\\?/[^"]+)"', page_text)]
    for u in urls[:2]:
        st, final, ctype, data = curl(H.unescape(u), binary=True, limit=3_000_000)
        if st != 200 or len(data) < 300: continue
        try: im = load_image(data)
        except Exception: continue
        if not good_icon(im, 60, 1.3): return im, u
    return None, ""


# ---------------------------------------------------------------------------------------------------------------- one company
def work(item):
    name, src = item["name"], item["src"]
    res = {"name": name, "n": item["n"], "ats": src.get("ats"), "token": src.get("token")}
    tried = []
    sites = []                                      # (domain, how) in order of trust
    if item.get("site"): sites.append((item["site"], "known"))
    if name in SITES: sites.append((SITES[name], "hand"))
    bsite, btext = board_site(src, name) if not sites else (None, "")
    if bsite:
        if root_domain(bsite) != bsite: sites.append((root_domain(bsite), "board-link"))      # gear.acme.com: acme.com first
        sites.append((bsite, "board-link"))
    if not sites:
        for d in name_candidates(name, src): sites.append((d, "name"))
    for d, how in sites:
        st, final, text = home(d)
        if blocked(st, text) or not text:
            tried.append(f"{d}: {'blocked' if text or st in (403, 429, 503) else 'no page'} {st}"); continue
        if PARKED.search(text[:20000]): tried.append(f"{d}: parked"); continue
        if how == "name":
            names, b = head_names(text), base_name(name)
            title_ok = len(b) >= 4 and (b in names or base_name(name, " ") in names)
            ev = board_evidence(src, text)
            if not ev and title_ok and (len(b) < 6 or generic(name) or len(b) < 8 and b in WORDS):
                cst, cfinal, _, ctext = curl(urljoin(final, "/careers"))       # the careers page, which usually links to the board
                ev = cst == 200 and board_evidence(src, ctext)
            # without a link to our board, the address itself must be the company's whole name or the name it uses on its board:
            # "The Hartford" is not hartford.com, "The Aerospace Corporation" is not aerospace.com (25 Nov 2026)
            fhost, ten = host_of(final), tenant_of(src)
            own = label_of(d) == norm(name) or (ten and not ten.isdigit() and label_of(d) == ten)
            if not ev and not (title_ok and own and len(b) >= 6 and not generic(name) and label_of(fhost) in (label_of(d), b, ten)):
                tried.append(f"{d}: not sure it is theirs (title {'yes' if title_ok else 'no'}, board link no)"); continue
            how = "name+board-link" if ev else "name+title"
        im, iu, why = site_icon(final, text)
        if im is not None:
            save_icon(im, slugify(name))
            res.update(ok=True, site=d, how=how, icon=iu)
            return res
        tried.append(f"{d}: no usable icon ({'; '.join(why[:4])})")
    if btext or (src.get("ats") or "").lower() == "workday":
        im, iu = board_logo(src, btext)
        if im is not None:
            save_icon(im, slugify(name))
            res.update(ok=True, site=f"board:{src.get('ats')}/{src.get('token')}", how="board-logo", icon=iu)
            return res
    res.update(ok=False, tried=tried, site_tried=name in SITES)
    return res


def companies():
    """[(name, open jobs)] most first, from the live site: the 500 tiles of /companies/ and data/company-directory.json."""
    _, _, _, page = curl(f"{FULL}/companies/", limit=5_000_000)
    out = [(H.unescape(m.group(2)), int(m.group(1))) for m in
           re.finditer(r'<li data-n="[^"]*" data-o="(\d+)"[^>]*><a class="tile"[^>]*>.*?<span class="n">([^<]*)</span>', page)]
    _, _, _, rest = curl(f"{FULL}/data/company-directory.json", limit=50_000_000)
    out += [(r[0], r[2]) for r in json.loads(rest)]
    return out


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3000
    retry = any(a.startswith("--retry") for a in sys.argv)  # try again the sites that had no usable icon (after SVG and WebP icons were added)
    first = [a for a in sys.argv[2:] if not a.startswith("--")]  # names to do first (the home page's companies)
    srcs = {}
    for f in sorted(ROOT.glob("sources*.json")):
        if "candidates" in f.name: continue
        for s in json.loads(f.read_text()):
            srcs.setdefault(s["name"], s)
    known = json.loads(MAP.read_text()) if MAP.exists() else {}
    since = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--retry-before=")), 10 ** 9)   # retry only records older than this line
    done, last, line_of = set(), {}, {}
    if LOG.exists():
        for i, line in enumerate(LOG.read_text().splitlines(), 1):
            try: r = json.loads(line)
            except ValueError: continue
            last[r["name"]], line_of[r["name"]] = r, i            # the latest word on each company counts
        for r in last.values():
            old = line_of[r["name"]] < since
            again = (r["name"] in SITES and not r.get("site_tried")) or (retry and old and (any("no usable icon" in t or ": blocked 200" in t for t in r.get("tried", [])) or r.get("ats") == "workday"))
            if r.get("ok") or not again: done.add(r["name"])      # a failure is tried again once a hand-checked site is added
    have = {f.stem for f in OUT.glob("*.png")}
    allc = companies()
    order = sorted(allc[:limit], key=lambda c: (c[0] not in first, -c[1]))
    todo = [{"name": n, "n": c, "src": srcs.get(n, {}), "site": (known.get(n) or "") if not (known.get(n) or "").startswith("board:") else ""}
            for n, c in order if slugify(n) not in have and n not in done and n in srcs]
    print(f"{len(allc):,} companies; {len(todo):,} of the first {limit:,} to try", flush=True)
    found = 0
    with cf.ThreadPoolExecutor(4) as ex, open(LOG, "a") as log:
        for i, r in enumerate(ex.map(work, todo)):
            log.write(json.dumps(r, ensure_ascii=False) + "\n"); log.flush()
            if r.get("ok"):
                found += 1
                with _lock:
                    known[r["name"]] = r["site"]
            if i % 25 == 24:
                MAP.write_text(json.dumps(known, ensure_ascii=False, indent=1, sort_keys=True))
                print(f"  {i + 1:,} of {len(todo):,}: {found:,} logos", flush=True)
    MAP.write_text(json.dumps(known, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"done: {found:,} new logos of {len(todo):,} tried", flush=True)
    dedupe()


def dedupe():
    """The same picture for two different companies is a website builder's, a host's or a parent company's icon, not each one's own
    logo: a logo found here that equals another company's file is dropped (two boards of one company, "acme" and "acme-uk", may share)."""
    new = set()
    for line in LOG.read_text().splitlines():
        try: r = json.loads(line)
        except ValueError: continue
        if r.get("ok"): new.add(slugify(r["name"]))
    same = {}
    for f in OUT.glob("*.png"): same.setdefault(hashlib.md5((OUT / "s" / f.name).read_bytes() if (OUT / "s" / f.name).exists() else f.read_bytes()).hexdigest(), []).append(f)
    known = json.loads(MAP.read_text())
    dropped = []
    for files in same.values():
        if len(files) < 2 or len({f.stem.split("-")[0] for f in files}) < 2: continue
        for f in files:
            if f.stem in new:
                f.unlink(); (OUT / "s" / f.name).unlink(missing_ok=True); dropped.append(f.stem)
                known = {k: v for k, v in known.items() if slugify(k) != f.stem}
    MAP.write_text(json.dumps(known, ensure_ascii=False, indent=1, sort_keys=True))
    if dropped: print("dropped, the same icon as another company's:", ", ".join(sorted(dropped)), flush=True)


if __name__ == "__main__":
    dedupe() if sys.argv[1:2] == ["--dedupe"] else main()
