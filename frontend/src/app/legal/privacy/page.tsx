import { LegalDocumentPage } from "@/components/legal-document-page";
import { legalCopy } from "@/lib/legal-copy";

export default function PrivacyPage() {
  return <LegalDocumentPage {...legalCopy.privacy} />;
}
