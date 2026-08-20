import type { Metadata } from "next";
import PageHeader from "../components/PageHeader";
import PublicShell from "../components/PublicShell";
import { getSiteSettings } from "../../lib/news";
import ContactForm from "./ContactForm";

export const metadata: Metadata = { title: "Contact", description: "Contact The Republic Bulletin newsroom." };
const PURPOSES = [{ key: "general", label: "General", text: "General questions about the publication." }, { key: "tips", label: "News tips", text: "Information or documents the newsroom should review." }, { key: "corrections", label: "Corrections", text: "Report a possible factual error in a published story." }, { key: "advertising", label: "Advertising", text: "Commercial and sponsorship enquiries." }, { key: "press", label: "Press", text: "Media and institutional enquiries." }] as const;
export default async function ContactPage() { const settings = await getSiteSettings(); return <PublicShell><PageHeader eyebrow="Newsroom contact" title="Contact us" description="Choose the purpose that best matches your enquiry." crumbs={[{ label: "Contact" }]} /><div className="contact-purpose-grid">{PURPOSES.map((purpose) => { const address = settings.contact?.[purpose.key]; return <section key={purpose.key}><h2>{purpose.label}</h2><p>{purpose.text}</p>{address ? <a href={`mailto:${address}`}>{address}</a> : <p className="configuration-note">Contact address not yet configured.</p>}{purpose.key === "tips" && <small>Standard email may expose identifying metadata. The publication does not currently claim that this channel is anonymous or end-to-end encrypted.</small>}</section>; })}</div><ContactForm /></PublicShell>; }
