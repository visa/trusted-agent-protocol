import { describe, test, expect } from "bun:test";
import { getAuthorityService } from "./module";
import forge from 'node-forge';

describe("Authority Service", () => {
    const authority = getAuthorityService();

    test("should provide CA certificate", () => {
        const cert = authority.getCACertificatePem();
        expect(cert).toContain("BEGIN CERTIFICATE");
    });

    test("should sign a valid CSR", () => {
        // Generate keys for agent
        const keys = forge.pki.rsa.generateKeyPair(2048);
        const csr = forge.pki.createCertificationRequest();
        csr.publicKey = keys.publicKey;
        csr.setSubject([{
            name: 'commonName',
            value: 'test-agent'
        }]);
        csr.sign(keys.privateKey);
        const csrPem = forge.pki.certificationRequestToPem(csr);

        const certPem = authority.signCSR(csrPem, 'test-agent');
        expect(certPem).toContain("BEGIN CERTIFICATE");

        const cert = forge.pki.certificateFromPem(certPem);
        expect(cert.subject.getField('CN').value).toBe('test-agent');

        // Verify against CA
        const caCertPem = authority.getCACertificatePem();
        const caCert = forge.pki.certificateFromPem(caCertPem);
        expect(caCert.verify(cert)).toBe(true);
    });

    test("should reject invalid CSR", () => {
        const keys = forge.pki.rsa.generateKeyPair(2048);
        const csr = forge.pki.createCertificationRequest();
        csr.publicKey = keys.publicKey;
        csr.setSubject([{
            name: 'commonName',
            value: 'test-agent'
        }]);
        // Don't sign or sign with wrong key
        const otherKeys = forge.pki.rsa.generateKeyPair(1024);
        csr.sign(otherKeys.privateKey);
        const csrPem = forge.pki.certificationRequestToPem(csr);

        expect(() => authority.signCSR(csrPem, 'test-agent')).toThrow();
    });
});
