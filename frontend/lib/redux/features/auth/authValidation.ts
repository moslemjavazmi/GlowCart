import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().trim().email("ایمیل معتبر وارد کنید."),
  password: z.string().min(1, "رمز عبور الزامی است."),
});

export const registerSchema = z
  .object({
    email: z.string().trim().email("ایمیل معتبر وارد کنید."),
    password: z
      .string()
      .min(8, "رمز عبور باید حداقل ۸ کاراکتر باشد."),
    password_confirm: z.string().min(1, "تکرار رمز عبور الزامی است."),
  })
  .refine((data) => data.password === data.password_confirm, {
    message: "رمزهای عبور یکسان نیستند.",
    path: ["password_confirm"],
  });

export const verifyEmailSchema = z.object({
  email: z.string().trim().email("ایمیل معتبر وارد کنید."),
  code: z
    .string()
    .regex(/^\d{6}$/, "کد تأیید باید دقیقاً ۶ رقم باشد."),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
export type RegisterFormValues = z.infer<typeof registerSchema>;
export type VerifyEmailFormValues = z.infer<typeof verifyEmailSchema>;