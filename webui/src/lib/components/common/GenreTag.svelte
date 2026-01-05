<script>
    /**
     * GenreTag - Styled tag/badge component for genres, tags, status indicators
     *
     * Variants:
     * - default: muted zinc styling
     * - genre: orange accent for genres
     * - tag: subtle gray for tags
     * - status: green for status (Ongoing/Completed)
     * - warning: red for content warnings
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
        background: rgba(63, 63, 70, 0.8);
        color: #a1a1aa;
        border-color: rgba(82, 82, 91, 0.7);
    }

    .genre-tag.genre {
        background: rgba(249, 115, 22, 0.2);
        color: #fb923c;
        border-color: rgba(249, 115, 22, 0.3);
    }

    .genre-tag.tag {
        background: rgba(63, 63, 70, 0.5);
        color: #71717a;
        border-color: rgba(82, 82, 91, 0.4);
    }

    .genre-tag.status {
        background: rgba(34, 197, 94, 0.2);
        color: #4ade80;
        border-color: rgba(34, 197, 94, 0.3);
    }

    .genre-tag.warning {
        background: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border-color: rgba(239, 68, 68, 0.3);
    }
</style>
