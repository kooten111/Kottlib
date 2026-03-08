<script>
    /**
     * GenreTag - Styled tag/badge component for genres, tags, status indicators.
     * Colors are derived from active theme variables.
     */
    export let variant = "default";
</script>

<span class="genre-tag {variant}">
    <slot />
</span>

<style>
    .genre-tag {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.5rem;
        font-size: 0.7rem;
        font-weight: 500;
        border-radius: 4px;
        border: 1px solid;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        white-space: nowrap;
    }

    .genre-tag.default {
        background: color-mix(in srgb, var(--color-tertiary-bg) 82%, transparent);
        color: var(--color-text-secondary);
        border-color: var(--color-border-strong);
    }

    .genre-tag.genre {
        background: color-mix(in srgb, var(--color-accent) 20%, transparent);
        color: var(--color-accent);
        border-color: color-mix(in srgb, var(--color-accent) 35%, transparent);
    }

    .genre-tag.tag {
        background: color-mix(in srgb, var(--color-tertiary-bg) 68%, transparent);
        color: var(--color-text-muted);
        border-color: var(--color-border);
    }

    .genre-tag.status {
        background: color-mix(in srgb, var(--color-success) 20%, transparent);
        color: var(--color-success);
        border-color: color-mix(in srgb, var(--color-success) 35%, transparent);
    }

    .genre-tag.warning {
        background: color-mix(in srgb, var(--color-error) 20%, transparent);
        color: var(--color-error);
        border-color: color-mix(in srgb, var(--color-error) 35%, transparent);
    }
</style>
