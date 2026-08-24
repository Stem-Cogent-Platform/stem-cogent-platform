import { LegalDocumentPage } from "@/components/legal-document-page";
import { legalCopy } from "@/lib/legal-copy";

export default function TermsPage() {
  return <LegalDocumentPage {...legalCopy.terms} />;
}
