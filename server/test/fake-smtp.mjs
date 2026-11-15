// A mail server for the tests: TLS from the first byte (like port 465), EHLO, AUTH LOGIN, MAIL FROM, RCPT TO, DATA, QUIT. It keeps what
// it was told and can be made to answer with an error at any step. It listens on 127.0.0.1 only and nothing leaves the machine.
//   const s = await fakeSmtp({ user, pass }); ... s.port, s.ca, s.letters, s.sessions; s.failNext.push({ at: 'RCPT', reply: '450 try later' });
//   s.silentAfterData = 1 (the next letter is taken and never answered); await s.close();
import tls from 'node:tls';
import { selfSigned } from './cert.mjs';

export async function fakeSmtp({ user = 'box@site.test', pass = 'mailbox-pass', greeting = '220 fake.smtp ESMTP ready' } = {}) {
  const { cert, key } = selfSigned('localhost');
  const state = { letters: [], sessions: [], failNext: [], logins: [], dropNext: 0, silentAfterData: 0 };
  const server = tls.createServer({ cert, key }, (sock) => {
    if (state.dropNext > 0) { state.dropNext--; sock.destroy(); return; }
    const s = { lines: [], authed: false }; state.sessions.push(s);
    let buf = '', mode = 'cmd', data = [], from = '', to = [], login = [];
    const say = (l) => sock.write(l + '\r\n');
    const fail = (at) => { const i = state.failNext.findIndex((f) => f.at === at); if (i < 0) return false; say(state.failNext.splice(i, 1)[0].reply); return true; };
    say(greeting);
    sock.setEncoding('utf8');
    sock.on('error', () => {});
    sock.on('data', (chunk) => {
      buf += chunk; let i;
      while ((i = buf.indexOf('\r\n')) >= 0) {
        const line = buf.slice(0, i); buf = buf.slice(i + 2);
        if (mode === 'data') {
          if (line === '.') {
            mode = 'cmd';
            if (state.silentAfterData > 0) { state.silentAfterData--; state.letters.push({ from, to: [...to], data: '', raw: '', unanswered: true }); data = []; continue; }   // takes the letter, never answers
            if (fail('DATA_END')) continue;
            state.letters.push({ from, to: [...to], data: data.map((l) => (l.startsWith('..') ? l.slice(1) : l)).join('\r\n'), raw: data.join('\r\n') }); data = [];
            say('250 2.0.0 Ok: queued as FAKE' + state.letters.length);
          } else data.push(line);
          continue;
        }
        s.lines.push(line);
        if (mode === 'user') { login.push(Buffer.from(line, 'base64').toString()); mode = 'pass'; say('334 UGFzc3dvcmQ6'); continue; }
        if (mode === 'pass') {
          login.push(Buffer.from(line, 'base64').toString()); mode = 'cmd'; state.logins.push(login); s.authed = login[0] === user && login[1] === pass;
          if (fail('AUTH_PASS')) continue;
          say(s.authed ? '235 2.7.0 Authentication successful' : '535 5.7.8 Authentication failed'); login = []; continue;
        }
        const cmd = line.slice(0, 4).toUpperCase();
        if (cmd === 'EHLO') { if (!fail('EHLO')) { sock.write('250-fake.smtp\r\n250-AUTH LOGIN PLAIN\r\n250 8BITMIME\r\n'); } }
        else if (line.toUpperCase() === 'AUTH LOGIN') { if (!fail('AUTH')) { mode = 'user'; say('334 VXNlcm5hbWU6'); } }
        else if (cmd === 'MAIL') { if (!fail('MAIL')) { if (!s.authed) say('530 5.7.0 Authentication required'); else { from = line.slice(10).replace(/[<>]/g, ''); to = []; say('250 2.1.0 Ok'); } } }
        else if (cmd === 'RCPT') { if (!fail('RCPT')) { to.push(line.slice(8).replace(/[<>]/g, '')); say('250 2.1.5 Ok'); } }
        else if (cmd === 'DATA') { if (!fail('DATA')) { mode = 'data'; say('354 End data with <CR><LF>.<CR><LF>'); } }
        else if (cmd === 'QUIT') { say('221 2.0.0 Bye'); sock.end(); }
        else say('502 5.5.2 Error: command not recognized');
      }
    });
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  return Object.assign(state, { port: server.address().port, ca: cert, close: () => new Promise((r) => server.close(r)) });
}
