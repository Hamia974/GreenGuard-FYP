import type { VariantProps } from "class-variance-authority"
import Link from "next/link"
import type * as React from "react"

import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

/** Navigation styled as a button: a real Next.js `<Link>` (native `<a>` semantics)
 * sharing the Button variants. Use `Button` for actions, `LinkButton` for routes. */
function LinkButton({
  className,
  variant = "default",
  size = "default",
  ...props
}: React.ComponentProps<typeof Link> & VariantProps<typeof buttonVariants>) {
  return (
    <Link
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { LinkButton }
