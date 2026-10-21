// SPDX-License-Identifier: GPL-3.0-only
const fs = require('fs');
const path = require('path');
const cp = require('child_process');
const config = JSON.parse(fs.readFileSync(process.env.WVKBD_SIGNING_CONFIG, 'utf8'));
const { DecipherUtil } = require(process.env.WVKBD_DECIPHER_UTIL);
const java = process.env.WVKBD_JAVA;
const jar = process.env.WVKBD_HAP_SIGN_TOOL;
const source = process.env.WVKBD_UNSIGNED_DIR;
const out = process.env.WVKBD_SIGNED_DIR;
const bundles = ['org.openharmony.wvkbd', 'org.openharmony.wvkbd.test'];
const launcher = path.join(__dirname, 'HapSignToolLauncher.java');
const classes = path.join(path.dirname(out), 'signer-launcher-classes');
const classFile = path.join(classes, 'HapSignToolLauncher.class');
const compiler = path.join(path.dirname(java), 'javac.exe');

if (Object.keys(config).length !== bundles.length ||
    bundles.some(bundle => !Object.prototype.hasOwnProperty.call(config, bundle))) {
  throw new Error('Signing config must contain exactly the task bundles');
}
fs.mkdirSync(classes, { recursive: false });
const compile = cp.spawnSync(compiler, ['-encoding', 'UTF-8', '-d', classes, launcher],
  { encoding: 'utf8', windowsHide: true });
if (compile.status !== 0 || !fs.existsSync(classFile)) {
  console.log('SIGNER_LAUNCHER=FAIL');
  process.exitCode = 1;
  return;
}
fs.mkdirSync(out, { recursive: false });

function secretInput(values) {
  const chunks = [];
  for (const value of values) {
    const bytes = Buffer.from(value, 'utf8');
    const length = Buffer.alloc(4);
    length.writeInt32BE(bytes.length);
    chunks.push(length, bytes);
  }
  return Buffer.concat(chunks);
}

function runSigner(args, secrets = []) {
  const classPath = [classes, jar].join(path.delimiter);
  const result = cp.spawnSync(java, ['-cp', classPath, 'HapSignToolLauncher', jar,
    String(secrets.length), ...args], {
    encoding: 'utf8', input: secretInput(secrets), windowsHide: true,
    maxBuffer: 4 * 1024 * 1024
  });
  return result.status === 0;
}

let failed = false;
for (const bundle of bundles) {
  const material = config[bundle].material;
  const isEditor = bundle.endsWith('.test');
  const input = path.join(source, isEditor ? 'editor-unsigned.hap' : 'ime-unsigned.hap');
  const signed = path.join(out, isEditor ? 'editor-signed.hap' : 'ime-signed.hap');
  const storePass = DecipherUtil.decryptPwd(path.dirname(material.storeFile),
    material.storePassword, 'signing.storePassword');
  const keyPass = DecipherUtil.decryptPwd(path.dirname(material.storeFile),
    material.keyPassword, 'signing.keyPassword');
  const args = ['sign-app', '-mode', 'localSign', '-keyAlias', material.keyAlias,
    '-keyPwd', '@WVKBD_KEY_PASSWORD@', '-appCertFile', material.certpath, '-profileFile', material.profile,
    '-profileSigned', '1', '-inFile', input, '-signAlg', material.signAlg,
    '-keystoreFile', material.storeFile, '-keystorePwd', '@WVKBD_STORE_PASSWORD@', '-outFile', signed,
    '-compatibleVersion', '23', '-signCode', '1', '-permSign', '1', '-pwdInputMode', '0'];
  let ok = runSigner(args, [storePass, keyPass]) && fs.existsSync(signed);
  if (ok) {
    const certChain = path.join(out, isEditor ? 'editor-cert-chain.cer' : 'ime-cert-chain.cer');
    const extractedProfile = path.join(out,
      isEditor ? 'editor-verified-profile.p7b' : 'ime-verified-profile.p7b');
    ok = runSigner(['verify-app', '-inFile', signed, '-outCertChain', certChain,
      '-outProfile', extractedProfile]);
  }
  console.log(`${bundle}:SIGN_AND_VERIFY=${ok ? 'PASS' : 'FAIL'}`);
  failed ||= !ok;
}

if (failed) {
  process.exitCode = 1;
} else {
  console.log('SIGNED_HAPS=PASS count=2');
}
