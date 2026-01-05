<script>
    import { createEventDispatcher } from "svelte";
    import { FolderOpen, BookOpen, Star, Clock, Play } from "lucide-svelte";
    import { getCoverUrl } from "$lib/api/comics";
    import GenreTag from "$lib/components/common/GenreTag.svelte";

    export let item; // The folder/series object
    export let libraryId;
    export let onClick = null;

    const dispatch = createEventDispatcher();

    // Determine type and styling
    $: isCollection = item.type === "collection";
    $: typeLabel = isCollection ? "COLLECTION" : "SERIES";
    $: badgeClass = isCollection
        ? "text-orange-400 border-orange-500/30"
        : "text-blue-400 border-blue-500/30";

    $: metadata = item.metadata || item || {};
    $: coverHash = item.cover_hash || item.coverHash;
    $: coverUrl = coverHash ? getCoverUrl(libraryId, coverHash) : null;

    // Stats
    $: subCollections = item.sub_collections || 0; // count of sub-folders
    $: totalIssues = item.total_issues || 0; // total comics
    $: rating = metadata.rating || 0;

    // Progress (mock for now if not provided, or calculated from item)
    $: progress = item.progress || {
        percentage: 0,
        read: 0,
        total: totalIssues,
    };

    $: displayName = item.name || item.title;

    function handleClick() {
        if (onClick) {
            onClick(item);
        } else {
            dispatch("click", item);
        }
    }

    // Generate gradient colors from hash (simple hash-based color fallback)
    function getGradientColors(hash) {
        if (!hash) return ["#3f3f46", "#18181b"];
        const colorPairs = [
            ["#f97316", "#dc2626"],
            ["#3b82f6", "#8b5cf6"],
            ["#22c55e", "#14b8a6"],
            ["#ec4899", "#f43f5e"],
            ["#eab308", "#f97316"],
            ["#6366f1", "#3b82f6"],
            ["#06b6d4", "#0ea5e9"],
            ["#a855f7", "#ec4899"],
        ];
        let sum = 0;
        for (let i = 0; i < hash.length; i++) sum += hash.charCodeAt(i);
        return colorPairs[sum % colorPairs.length];
    }

    $: gradientColors = getGradientColors(coverHash || displayName);
</script>

<button
    class="group relative bg-zinc-900 rounded-xl overflow-hidden border border-zinc-800 hover:border-orange-500/50 transition-all hover:scale-[1.02] hover:shadow-xl hover:shadow-orange-500/5 text-left w-full flex flex-col h-full"
    on:click={handleClick}
>
    <!-- Collection Stack Effect -->
    {#if isCollection}
        <div
            class="absolute -top-1.5 left-3 right-3 h-3 bg-zinc-800 rounded-t-xl border-t border-x border-zinc-700"
        ></div>
        <div
            class="absolute -top-0.5 left-1.5 right-1.5 h-2 bg-zinc-850 rounded-t-lg"
        ></div>
    {/if}

    <!-- Cover Image Area -->
    <div class="relative aspect-[1/1.414] overflow-hidden w-full bg-zinc-800">
        {#if coverUrl}
            <img
                src={coverUrl}
                alt={displayName}
                class="w-full h-full object-cover rounded-none transition-transform duration-500 group-hover:scale-105"
                loading="lazy"
            />
        {:else}
            <div
                class="w-full h-full flex items-center justify-center p-4 bg-gradient-to-br"
                style="background-image: linear-gradient(135deg, {gradientColors[0]}, {gradientColors[1]})"
            >
                <div class="text-white/50">
                    {#if isCollection}
                        <FolderOpen size={48} />
                    {:else}
                        <BookOpen size={48} />
                    {/if}
                </div>
                <div
                    class="absolute bottom-0 left-0 right-0 p-2 bg-black/40 backdrop-blur-sm"
                >
                    <span
                        class="text-xs text-white font-medium line-clamp-2 text-center"
                        >{displayName}</span
                    >
                </div>
            </div>
        {/if}

        <!-- Type Badge -->
        <div
            class="absolute top-2 left-2 px-2 py-0.5 bg-zinc-900/90 backdrop-blur rounded text-[10px] font-bold border {badgeClass}"
        >
            {typeLabel}
        </div>

        <!-- Progress Badge (if started) -->
        {#if progress.percentage > 0}
            <div
                class="absolute top-2 right-2 px-2 py-0.5 bg-zinc-900/90 backdrop-blur rounded text-[10px] font-medium text-zinc-300"
            >
                {progress.read}/{progress.total}
            </div>
        {/if}

        <!-- Hover Overlay -->
        <div
            class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-3"
        >
            {#if metadata.description || metadata.synopsis}
                <p class="text-xs text-zinc-300 line-clamp-3 mb-2">
                    {metadata.description || metadata.synopsis}
                </p>
            {/if}
            <div class="flex items-center gap-2 mt-auto">
                <Play class="w-4 h-4 text-orange-400 fill-orange-400" />
                <span class="text-xs text-orange-400 font-medium"
                    >Browse {isCollection ? "Collection" : "Series"}</span
                >
            </div>
        </div>

        <!-- Progress Bar (Bottom Line) -->
        {#if progress.percentage > 0}
            <div class="absolute bottom-0 left-0 right-0 h-1 bg-black/40">
                <div
                    class="h-full bg-orange-500"
                    style="width: {progress.percentage}%"
                ></div>
            </div>
        {/if}
    </div>

    <!-- Info Area -->
    <div class="p-3 space-y-2 flex-1 flex flex-col w-full bg-zinc-900">
        <h3
            class="font-semibold text-white text-sm line-clamp-2 group-hover:text-orange-400 transition-colors"
            title={displayName}
        >
            {displayName}
        </h3>

        {#if !isCollection && metadata.writer}
            <p class="text-xs text-zinc-500 truncate">{metadata.writer}</p>
        {/if}

        {#if isCollection && metadata.genres}
            <div class="flex flex-wrap gap-1">
                {#each Array.isArray(metadata.genres) ? metadata.genres : metadata.genres.split(",") as genre}
                    <span
                        class="text-[10px] px-1.5 py-0.5 bg-zinc-800 text-zinc-400 rounded border border-zinc-700/50"
                        >{genre.trim()}</span
                    >
                {/each}
            </div>
        {/if}

        <div class="mt-auto flex items-center gap-3 text-xs text-zinc-500 pt-1">
            {#if isCollection}
                {#if subCollections > 0}
                    <span class="flex items-center gap-1"
                        ><FolderOpen class="w-3 h-3" />{subCollections}</span
                    >
                {/if}
                <span class="flex items-center gap-1"
                    ><BookOpen class="w-3 h-3" />{totalIssues}</span
                >
            {:else}
                <span class="flex items-center gap-1"
                    ><BookOpen class="w-3 h-3" />{totalIssues} issues</span
                >
            {/if}

            {#if rating > 0}
                <span class="flex items-center gap-1 ml-auto">
                    <Star
                        class="w-3 h-3 text-yellow-500 fill-yellow-500"
                    />{rating}
                </span>
            {/if}
        </div>
    </div>
</button>
