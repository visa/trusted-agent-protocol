export interface IAuthorityService {
    /**
     * Returns the CA certificate in PEM format.
     */
    getCACertificatePem(): string;

    /**
     * Signs a CSR for an agent and returns the certificate in PEM format.
     * @param csrPem The CSR in PEM format.
     * @param agentId The Agent ID (Common Name) for the certificate.
     */
    signCSR(csrPem: string, agentId: string): string;
}
