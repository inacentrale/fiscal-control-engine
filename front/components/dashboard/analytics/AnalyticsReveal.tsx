"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

export default function AnalyticsReveal({
  children,
  delay = 0,
}: {
  children: ReactNode;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18, scale: 0.985 }}
      transition={{ duration: 0.42, delay, ease: [0.22, 1, 0.36, 1] }}
      viewport={{ once: true, margin: "0px 0px -12% 0px" }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
    >
      {children}
    </motion.div>
  );
}
