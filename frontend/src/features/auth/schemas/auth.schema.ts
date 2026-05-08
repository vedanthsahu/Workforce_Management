import { ALLOWED_EMAIL_DOMAINS } from "@/config/allowedDomains";
import { z } from "zod";


export const emailSchema = z.object({
  email: z
    .string()
    .min(1, "Email is required")
    .email("Please enter a valid email address")
    .refine((email) => {
      const domain = email.split("@")[1]?.toLowerCase();
      return domain !== undefined && ALLOWED_EMAIL_DOMAINS.includes(domain);
    }, {
      message: `Please use your organization email address. External domains aren’t supported.`,
    }),
});

export type EmailFormValues = z.infer<typeof emailSchema>;