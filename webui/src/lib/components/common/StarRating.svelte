<script>
    /**
     * StarRating - Simple star rating display component
     */
    import { Star } from "lucide-svelte";

    export let rating = 0;
</script>

<div class="star-rating">
    <Star class="star-icon" />
    <span class="rating-value">{rating.toFixed(1)}</span>
</div>

<style>
    .star-rating {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    :global(.star-rating .star-icon) {
        width: 1rem;
        height: 1rem;
        color: #eab308;
        fill: #eab308;
    }

    .rating-value {
        font-size: 0.875rem;
        font-weight: 500;
        color: white;
    }
</style>
