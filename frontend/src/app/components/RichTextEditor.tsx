"use client";

import { useEffect, useRef } from "react";
import type Quill from "quill";
import "quill/dist/quill.snow.css";

interface RichTextEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export default function RichTextEditor({ value, onChange, placeholder }: RichTextEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const quillRef = useRef<Quill | null>(null);
  const valueRef = useRef(value);

  useEffect(() => {
    valueRef.current = value;
  }, [value]);

  useEffect(() => {
    if (!containerRef.current || quillRef.current) return;

    const initQuill = async () => {
      const { default: QuillEditor } = await import("quill");
      if (!containerRef.current || quillRef.current) return;

      const quill = new QuillEditor(containerRef.current, {
        theme: "snow",
        placeholder: placeholder || "Type your chronicle here...",
        modules: {
          toolbar: [
            [{ header: [1, 2, 3, false] }],
            ["bold", "italic", "underline", "strike"],
            [{ list: "ordered" }, { list: "bullet" }],
            ["link", "clean"],
          ],
        },
      });

      quillRef.current = quill;

      if (valueRef.current) {
        quill.root.innerHTML = valueRef.current;
      }

      quill.on("text-change", () => {
        const html = quill.root.innerHTML;
        if (html !== valueRef.current) {
          valueRef.current = html;
          onChange(html);
        }
      });
    };

    initQuill();
  }, [onChange, placeholder]);

  useEffect(() => {
    if (!quillRef.current) return;

    const currentHTML = quillRef.current.root.innerHTML;
    const isCurrentEmpty = currentHTML === "" || currentHTML === "<p><br></p>";
    const isNewEmpty = value === "" || value === "<p><br></p>";

    if (currentHTML !== value && !(isCurrentEmpty && isNewEmpty)) {
      quillRef.current.root.innerHTML = value || "";
      valueRef.current = value;
    }
  }, [value]);

  return (
    <div className="vintage-editor-wrapper">
      <div ref={containerRef} />
    </div>
  );
}
