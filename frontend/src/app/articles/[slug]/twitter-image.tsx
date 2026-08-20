import { createArticleSocialImage, socialImageSize } from "./social-image";

export const alt = "Article preview from The Republic Bulletin";
export const size = socialImageSize;
export const contentType = "image/png";

export default async function TwitterImage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return createArticleSocialImage(slug);
}
