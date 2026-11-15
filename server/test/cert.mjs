// A self-signed certificate for "localhost", made when the tests run (no key is kept in the repository, no openssl needed): an EC key
// from node:crypto and an X.509 certificate written out in DER by hand. Only the fake mail server of the tests uses it.
import { generateKeyPairSync, sign, randomBytes } from 'node:crypto';

const len = (n) => (n < 128 ? Buffer.from([n]) : n < 256 ? Buffer.from([0x81, n]) : Buffer.from([0x82, n >> 8, n & 255]));
const tlv = (tag, ...parts) => { const body = Buffer.concat(parts); return Buffer.concat([Buffer.from([tag]), len(body.length), body]); };
const seq = (...p) => tlv(0x30, ...p), set = (...p) => tlv(0x31, ...p);
const oid = (s) => { const n = s.split('.').map(Number), out = [40 * n[0] + n[1]];
  for (const v of n.slice(2)) { const b = []; let x = v; do { b.unshift(x & 127); x >>= 7; } while (x); out.push(...b.map((y, i) => (i < b.length - 1 ? y | 128 : y))); }
  return tlv(0x06, Buffer.from(out)); };
const int = (buf) => tlv(0x02, buf[0] & 0x80 ? Buffer.concat([Buffer.from([0]), buf]) : buf);
const time = (d) => tlv(0x18, Buffer.from(d.toISOString().replace(/[-:T]/g, '').slice(0, 14) + 'Z'));      // GeneralizedTime
const name = (cn) => seq(set(seq(oid('2.5.4.3'), tlv(0x0c, Buffer.from(cn)))));

export function selfSigned(host = 'localhost') {
  const { privateKey, publicKey } = generateKeyPairSync('ec', { namedCurve: 'prime256v1' });
  const alg = seq(oid('1.2.840.10045.4.3.2'));                              // ecdsa-with-SHA256
  const san = seq(oid('2.5.29.17'), tlv(0x04, seq(tlv(0x82, Buffer.from(host)))));
  const tbs = seq(tlv(0xa0, int(Buffer.from([2]))), int(randomBytes(8)), alg, name(host),
    seq(time(new Date(Date.now() - 86400000)), time(new Date(Date.now() + 86400000))), name(host),
    publicKey.export({ type: 'spki', format: 'der' }), tlv(0xa3, seq(san)));
  const der = seq(tbs, alg, tlv(0x03, Buffer.concat([Buffer.from([0]), sign('sha256', tbs, privateKey)])));
  const pem = '-----BEGIN CERTIFICATE-----\n' + der.toString('base64').match(/.{1,64}/g).join('\n') + '\n-----END CERTIFICATE-----\n';
  return { cert: pem, key: privateKey.export({ type: 'pkcs8', format: 'pem' }) };
}
