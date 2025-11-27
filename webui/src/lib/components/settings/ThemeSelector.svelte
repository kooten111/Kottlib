<script>
    import { themeStore } from "$stores/theme";
    import { getLightThemes, getDarkThemes } from "$lib/themes";
    import { Check } from "lucide-svelte";

    $: lightThemes = getLightThemes();
    $: darkThemes = getDarkThemes();

    function selectLightTheme(themeId) {
        themeStore.setLightTheme(themeId);
    }

    function selectDarkTheme(themeId) {
        themeStore.setDarkTheme(themeId);
    }
</script>

<div class="theme-selector">
    <div class="theme-section">
        <h3 class="section-title">Light Theme</h3>
        <p class="section-description">Choose the theme for light mode</p>
        <div class="theme-grid">
            {#each lightThemes as theme}
                <button
                    class="theme-card"
                    class:selected={$themeStore.lightTheme === theme.id}
                    on:click={() => selectLightTheme(theme.id)}
                >
                    <div class="theme-preview">
                        <div
                            class="preview-bg"
                            style="background: {theme.colors.bg};"
                        >
                            <div
                                class="preview-text"
                                style="color: {theme.colors.text};"
                            >
                                Aa
                            </div>
                            <div
                                class="preview-accent"
                                style="background: {theme.colors.accent};"
                            ></div>
                        </div>
                    </div>
                    <div class="theme-info">
                        <span class="theme-name">{theme.name}</span>
                        {#if $themeStore.lightTheme === theme.id}
                            <Check class="w-4 h-4 text-accent-orange" />
                        {/if}
                    </div>
                </button>
            {/each}
        </div>
    </div>

    <div class="theme-section">
        <h3 class="section-title">Dark Theme</h3>
        <p class="section-description">Choose the theme for dark mode</p>
        <div class="theme-grid">
            {#each darkThemes as theme}
                <button
                    class="theme-card"
                    class:selected={$themeStore.darkTheme === theme.id}
                    on:click={() => selectDarkTheme(theme.id)}
                >
                    <div class="theme-preview">
                        <div
                            class="preview-bg"
                            style="background: {theme.colors.bg};"
                        >
                            <div
                                class="preview-text"
                                style="color: {theme.colors.text};"
                            >
                                Aa
                            </div>
                            <div
                                class="preview-accent"
                                style="background: {theme.colors.accent};"
                            ></div>
                        </div>
                    </div>
                    <div class="theme-info">
                        <span class="theme-name">{theme.name}</span>
                        {#if $themeStore.darkTheme === theme.id}
                            <Check class="w-4 h-4 text-accent-orange" />
                        {/if}
                    </div>
                </button>
            {/each}
        </div>
    </div>
</div>

<style>
    .theme-selector {
        display: flex;
        flex-direction: column;
        gap: 3rem;
    }

    .theme-section {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .section-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--color-text);
        margin: 0;
    }

    .section-description {
        font-size: 0.875rem;
        color: var(--color-text-secondary);
        margin: 0;
    }

    .theme-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 1rem;
    }

    .theme-card {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        padding: 1rem;
        background: var(--color-secondary-bg);
        border: 2px solid transparent;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;
    }

    .theme-card:hover {
        border-color: var(--color-border-strong);
        transform: translateY(-2px);
    }

    .theme-card.selected {
        border-color: var(--color-accent);
        box-shadow: 0 0 0 3px rgba(255, 103, 64, 0.1);
    }

    .theme-preview {
        width: 100%;
        aspect-ratio: 16 / 9;
        border-radius: 6px;
        overflow: hidden;
        border: 1px solid var(--color-border);
    }

    .preview-bg {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        padding: 1rem;
    }

    .preview-text {
        font-size: 2rem;
        font-weight: 700;
    }

    .preview-accent {
        position: absolute;
        bottom: 0.5rem;
        right: 0.5rem;
        width: 1.5rem;
        height: 1.5rem;
        border-radius: 50%;
    }

    .theme-info {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
    }

    .theme-name {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--color-text);
    }

    @media (max-width: 768px) {
        .theme-grid {
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        }
    }
</style>
