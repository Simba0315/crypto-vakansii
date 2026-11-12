"""Probe public ATS job-board APIs for a list of crypto companies and print the ones that respond."""
import json, sys, concurrent.futures as cf
from net import get_json as probe

CANDIDATES = {
    "Coinbase": ["coinbase"], "Kraken": ["kraken", "kraken.com"], "OKX": ["okx"], "Binance": ["binance"],
    "Crypto.com": ["crypto", "cryptocom"], "Gemini": ["gemini"], "Ripple": ["ripple"], "Circle": ["circle"],
    "Consensys": ["consensys"], "Chainalysis": ["chainalysis"], "Fireblocks": ["fireblocks"], "BitGo": ["bitgo"],
    "Blockchain.com": ["blockchain"], "Bitpanda": ["bitpanda"], "Paxos": ["paxos"], "Anchorage Digital": ["anchorage", "anchoragedigital"],
    "Alchemy": ["alchemy"], "Aptos Labs": ["aptoslabs", "aptos"], "Ava Labs": ["avalabs"], "dYdX": ["dydx"],
    "Figment": ["figment"], "LayerZero": ["layerzerolabs", "layerzero"], "Magic Eden": ["magiceden"], "MoonPay": ["moonpay"],
    "Nansen": ["nansen"], "Offchain Labs": ["offchainlabs"], "Phantom": ["phantom"], "Solana Foundation": ["solanafoundation", "solana"],
    "Uniswap Labs": ["uniswaplabs", "uniswap"], "Wintermute": ["wintermute-trading", "wintermute"], "GSR": ["gsr", "gsrmarkets"],
    "Copper": ["copperco", "copper"], "BitMEX": ["bitmex"], "DFINITY": ["dfinity"], "Immutable": ["immutable"],
    "Ledger": ["ledger"], "1inch": ["1inch"], "Chainlink Labs": ["chainlink-labs", "chainlinklabs", "chainlink"],
    "Animoca Brands": ["animocabrands"], "Polygon Labs": ["polygon-labs", "polygonlabs", "polygon"], "Messari": ["messari"],
    "Galaxy": ["galaxydigitalservices", "galaxy"], "Bitso": ["bitso"], "Trust Wallet": ["trustwallet"], "KuCoin": ["kucoin"],
    "Bybit": ["bybit"], "Bitget": ["bitget"], "MEXC": ["mexc"], "Gate": ["gate", "gateio"], "HTX": ["htx", "huobi"],
    "Tether": ["tether"], "Bitfinex": ["bitfinex"], "TON Foundation": ["ton", "tonfoundation", "ton-foundation"],
    "Sui / Mysten Labs": ["mystenlabs"], "Near": ["near", "nearfoundation"], "Starkware": ["starkware"], "zkSync / Matter Labs": ["matterlabs", "matter-labs"],
    "Optimism": ["oplabs", "optimism"], "Arbitrum Foundation": ["arbitrumfoundation"], "Eigen Labs": ["eigenlabs", "eigen-labs"],
    "Lido": ["lido"], "Aave": ["aave", "avara"], "Compound": ["compound"], "MakerDAO / Sky": ["sky", "makerdao"],
    "OpenSea": ["opensea"], "Dune": ["dune", "duneanalytics"], "The Graph / Edge & Node": ["edgeandnode"], "Flashbots": ["flashbots"],
    "Paradigm": ["paradigm", "paradigm.xyz"], "a16z crypto": ["a16zcrypto"], "Pantera": ["pantera"], "Jump Crypto": ["jumpcrypto", "jumptrading"],
    "Cumberland / DRW": ["drweng", "drw"], "Amber Group": ["ambergroup"], "Keyrock": ["keyrock"], "B2C2": ["b2c2"],
    "Flow Traders": ["flowtraders"], "Kaiko": ["kaiko"], "Elliptic": ["elliptic"], "TRM Labs": ["trmlabs"],
    "Zerion": ["zerion"], "Safe": ["safe", "safe.global"], "Rainbow": ["rainbow"], "MetaMask": ["metamask"],
    "Exodus": ["exodus", "exodus54"], "Trezor / SatoshiLabs": ["satoshilabs"], "Tangem": ["tangem"], "Blockstream": ["blockstream"],
    "Lightning Labs": ["lightninglabs", "lightning"], "Bitwise": ["bitwise", "bitwiseinvestments"], "Grayscale": ["grayscaleinvestments", "grayscale"],
    "Robinhood Crypto": ["robinhood"], "Revolut": ["revolut"], "Bitstamp": ["bitstamp"], "Luno": ["luno"], "Bitvavo": ["bitvavo"],
    "WhiteBIT": ["whitebit"], "CEX.IO": ["cexio", "cex"], "Nexo": ["nexo"], "YouHodler": ["youhodler"], "Exness": ["exness"],
    "P2P.org": ["p2porg", "p2p"], "Everstake": ["everstake"], "Chorus One": ["chorusone", "chorus-one"], "Blockdaemon": ["blockdaemon"],
    "Nethermind": ["nethermind"], "OpenZeppelin": ["openzeppelin"], "Trail of Bits": ["trailofbits"], "CertiK": ["certik"],
    "Hacken": ["hacken"], "Halborn": ["halborn"], "Quantstamp": ["quantstamp"], "Zama": ["zama"], "Aztec": ["aztec", "aztecnetwork"],
    "Celestia": ["celestia", "celestiaorg"], "Monad": ["monad", "monadlabs", "monad.foundation"], "Berachain": ["berachain"], "Sei": ["sei", "seilabs"],
    "Injective": ["injective", "injectivelabs"], "Helius": ["helius"], "Jito": ["jito", "jito-labs", "jitolabs"], "Jupiter": ["jupiter", "jup"],
    "Raydium": ["raydium"], "Pyth / Douro Labs": ["dourolabs", "pyth"], "Wormhole": ["wormholefoundation", "wormhole"], "Axelar": ["axelar", "interoplabs"],
    "Ethena": ["ethena", "ethenalabs"], "Pendle": ["pendle"], "Morpho": ["morpho", "morpho-labs"], "Hyperliquid": ["hyperliquid"],
    "Kiln": ["kiln"], "Bitpay": ["bitpay"], "Ramp": ["ramp", "rampnetwork", "ramp.network"], "Transak": ["transak"], "Mercuryo": ["mercuryo"],
    "Sumsub": ["sumsub"], "Notabene": ["notabene"], "Chainstack": ["chainstack"], "QuickNode": ["quicknode"], "Infura": ["infura"],
    "Tenderly": ["tenderly"], "Gnosis": ["gnosis"], "Cow Protocol": ["cow", "cowprotocol", "cow-dao"], "Balancer": ["balancer", "balancerlabs"],
    "Curve": ["curve"], "Yearn": ["yearn"], "Synthetix": ["synthetix"], "GMX": ["gmx"], "Bitdeer": ["bitdeer"], "Marathon / MARA": ["mara", "marathon"],
    "Riot": ["riotplatforms", "riot"], "Core Scientific": ["corescientific"], "Swan": ["swan", "swanbitcoin"], "River": ["river", "riverfinancial"],
    "Strike": ["strike", "zap"], "Unchained": ["unchained", "unchainedcapital"], "Casa": ["casa"], "Fold": ["fold", "foldapp"],
}

def check(item):
    name, token = item
    found = []
    d = probe(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs")
    if d and d.get("jobs"): found.append(("greenhouse", token, len(d["jobs"])))
    d = probe(f"https://api.lever.co/v0/postings/{token}?mode=json&limit=500")
    if isinstance(d, list) and d: found.append(("lever", token, len(d)))
    d = probe(f"https://api.ashbyhq.com/posting-api/job-board/{token}")
    if d and d.get("jobs"): found.append(("ashby", token, len(d["jobs"])))
    return name, found

items = [(n, t) for n, ts in CANDIDATES.items() for t in ts]
out = {}
with cf.ThreadPoolExecutor(16) as ex:
    for name, found in ex.map(check, items):
        for f in found:
            out.setdefault(name, []).append(f)
res = []
for name, fs in sorted(out.items()):
    best = max(fs, key=lambda f: f[2])
    res.append({"name": name, "ats": best[0], "token": best[1], "count": best[2]})
    print(f"{name:28s} {best[0]:10s} {best[1]:24s} {best[2]}", file=sys.stderr)
print(f"\n{len(res)} companies, {sum(r['count'] for r in res)} jobs", file=sys.stderr)
json.dump(res, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
