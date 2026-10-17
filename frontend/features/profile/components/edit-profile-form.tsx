"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Camera, CheckCircle2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FieldError } from "@/components/ui/field-error";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { type EditProfileFormValues, editProfileSchema } from "@/features/profile/schemas";
import type { UserProfile } from "@/features/profile/types";
import { useParseApiError } from "@/lib/i18n/use-api-error";

// Mirrors UI_SPECIFICATION.md 16.6 "Profile Picture" (PNG/JPG/JPEG, max 5 MB).
const MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024;
const ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png"];

function extensionOf(filename: string): string {
  return filename.includes(".") ? filename.split(".").pop()!.toLowerCase() : "";
}

type ImageError = "unsupportedFormat" | "tooLarge";

interface EditProfileFormProps {
  profile: UserProfile;
  onSubmit: (values: EditProfileFormValues, imageFile?: File) => Promise<void>;
}

export function EditProfileForm({ profile, onSubmit }: EditProfileFormProps) {
  const t = useTranslations("profile.editProfile");
  const tCommon = useTranslations("common");
  const parseApiError = useParseApiError();
  const inputRef = useRef<HTMLInputElement>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [imageError, setImageError] = useState<ImageError | null>(null);
  const [imageFile, setImageFile] = useState<File | undefined>(undefined);
  const [previewUrl, setPreviewUrl] = useState<string | null>(profile.profileImage);
  const [isSaved, setIsSaved] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<EditProfileFormValues>({
    resolver: zodResolver(editProfileSchema),
    defaultValues: { fullName: profile.fullName },
  });

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setIsSaved(false);
    setImageError(null);
    if (!ALLOWED_EXTENSIONS.includes(extensionOf(file.name))) {
      setImageError("unsupportedFormat");
      return;
    }
    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      setImageError("tooLarge");
      return;
    }

    setImageFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const submit = async (values: EditProfileFormValues) => {
    setFormError(null);
    setIsSaved(false);
    try {
      await onSubmit(values, imageFile);
      setImageFile(undefined);
      setIsSaved(true);
    } catch (error) {
      setFormError(parseApiError(error).message);
    }
  };

  return (
    <form
      onSubmit={handleSubmit(submit)}
      onChange={() => setIsSaved(false)}
      noValidate
      className="flex flex-col gap-5"
    >
      {formError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      {isSaved && (
        <Alert>
          <CheckCircle2 />
          <AlertDescription>{t("success")}</AlertDescription>
        </Alert>
      )}

      <div className="flex items-center gap-4">
        <div className="relative flex size-16 shrink-0 items-center justify-center overflow-hidden rounded-full bg-primary/10 text-lg font-semibold text-primary">
          {previewUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={previewUrl} alt={t("photoPreviewAlt")} className="size-full object-cover" />
          ) : (
            profile.fullName.slice(0, 1).toUpperCase()
          )}
        </div>
        <div className="flex flex-col gap-1.5">
          <input
            ref={inputRef}
            type="file"
            accept="image/jpeg,image/jpg,image/png"
            className="hidden"
            onChange={handleFileChange}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => inputRef.current?.click()}
          >
            <Camera className="size-3.5" />
            {t("changePhoto")}
          </Button>
          <p className="text-xs text-muted-foreground">{t("photoHint")}</p>
          {imageError && <p className="text-xs text-error-text">{t(`imageErrors.${imageError}`)}</p>}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="fullName">{t("fullName")}</Label>
        <Input
          id="fullName"
          aria-invalid={!!errors.fullName}
          disabled={isSubmitting}
          className="h-11 rounded-[var(--radius-input)]"
          {...register("fullName")}
        />
        <FieldError message={errors.fullName?.message} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email">{t("email")}</Label>
        <Input
          id="email"
          value={profile.email}
          disabled
          className="h-11 rounded-[var(--radius-input)]"
        />
        <p className="text-xs text-muted-foreground">{t("emailLocked")}</p>
      </div>

      <Button type="submit" disabled={isSubmitting} className="h-11 w-fit rounded-2xl px-6">
        {isSubmitting ? (
          <>
            <Spinner /> {tCommon("saving")}
          </>
        ) : (
          tCommon("saveChanges")
        )}
      </Button>
    </form>
  );
}
