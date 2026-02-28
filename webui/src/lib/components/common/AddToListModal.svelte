<script>
    /**
     * AddToListModal - Modal for adding a comic to a reading list
     *
     * Features:
     * - Shows existing reading lists for the library
     * - Allows creating a new reading list
     * - Adds the comic to the selected list
     */
    import { X, Plus, BookOpen, Check, Loader2, ExternalLink } from 'lucide-svelte';
    import { getReadingLists, createReadingList, addComicToReadingList } from '$lib/api/readingLists';
    import { createEventDispatcher, onMount } from 'svelte';
    import { goto } from '$app/navigation';

    export let libraryId;
    export let comicId;
    export let show = false;

    const dispatch = createEventDispatcher();

    let readingLists = [];
    let isLoading = true;
    let error = null;
    let newListName = '';
    let isCreating = false;
    let addingToListId = null;
    let successListId = null;

    $: if (show && libraryId) {
        loadReadingLists();
    }

    async function loadReadingLists() {
        try {
            isLoading = true;
            error = null;
            readingLists = await getReadingLists(libraryId) || [];
        } catch (err) {
            console.error('Failed to load reading lists:', err);
            error = err.message;
        } finally {
            isLoading = false;
        }
    }

    async function handleCreateList() {
        if (!newListName.trim()) return;

        try {
            isCreating = true;
            error = null;
            const result = await createReadingList(libraryId, newListName.trim());
            if (result?.success) {
                newListName = '';
                await loadReadingLists();
                // Auto-add comic to the newly created list
                if (result.id && comicId) {
                    await handleAddToList(result.id);
                }
            }
        } catch (err) {
            console.error('Failed to create reading list:', err);
            error = err.message;
        } finally {
            isCreating = false;
        }
    }

    async function handleAddToList(listId) {
        if (!comicId) return;

        try {
            addingToListId = listId;
            error = null;
            await addComicToReadingList(libraryId, listId, comicId);
            successListId = listId;
            setTimeout(() => {
                successListId = null;
            }, 2000);
            dispatch('added', { listId, comicId });
        } catch (err) {
            console.error('Failed to add to reading list:', err);
            error = err.message;
        } finally {
            addingToListId = null;
        }
    }

    function close() {
        show = false;
        dispatch('close');
    }

    function handleBackdropClick(e) {
        if (e.target === e.currentTarget) {
            close();
        }
    }

    function handleKeydown(e) {
        if (e.key === 'Escape') {
            close();
        }
    }
</script>

{#if show}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="modal-backdrop" on:click={handleBackdropClick} on:keydown={handleKeydown} role="dialog" aria-modal="true" aria-label="Add to reading list" tabindex="-1">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">
                    <BookOpen class="w-5 h-5" />
                    Add to Reading List
                </h2>
                <button class="close-btn" on:click={close} aria-label="Close">
                    <X class="w-5 h-5" />
                </button>
            </div>

            {#if error}
                <div class="error-banner">
                    <p>{error}</p>
                </div>
            {/if}

            <div class="modal-body">
                <!-- Create new list -->
                <div class="create-list-section">
                    <form on:submit|preventDefault={handleCreateList} class="create-form">
                        <input
                            type="text"
                            bind:value={newListName}
                            placeholder="New reading list name..."
                            class="list-input"
                            disabled={isCreating}
                        />
                        <button
                            type="submit"
                            class="create-btn"
                            disabled={!newListName.trim() || isCreating}
                        >
                            {#if isCreating}
                                <Loader2 class="w-4 h-4 animate-spin" />
                            {:else}
                                <Plus class="w-4 h-4" />
                            {/if}
                            Create
                        </button>
                    </form>
                </div>

                <!-- Existing lists -->
                <div class="lists-section">
                    {#if isLoading}
                        <div class="loading">
                            <Loader2 class="w-5 h-5 animate-spin" />
                            <span>Loading lists...</span>
                        </div>
                    {:else if readingLists.length === 0}
                        <p class="empty-text">No reading lists yet. Create one above!</p>
                    {:else}
                        <div class="lists-grid">
                            {#each readingLists as list}
                                <div class="list-item-row">
                                    <button
                                        class="list-item"
                                        class:success={successListId === list.id}
                                        on:click={() => handleAddToList(list.id)}
                                        disabled={addingToListId === list.id}
                                    >
                                        <span class="list-name">{list.name}</span>
                                        <span class="list-action">
                                            {#if addingToListId === list.id}
                                                <Loader2 class="w-4 h-4 animate-spin" />
                                            {:else if successListId === list.id}
                                                <Check class="w-4 h-4 text-green-400" />
                                            {:else}
                                                <Plus class="w-4 h-4" />
                                            {/if}
                                        </span>
                                    </button>
                                    {#if successListId === list.id}
                                        <button
                                            class="view-list-link"
                                            on:click={() => { close(); goto(`/reading-lists/${libraryId}/${list.id}`); }}
                                        >
                                            <ExternalLink class="w-3.5 h-3.5" />
                                            View
                                        </button>
                                    {/if}
                                </div>
                            {/each}
                        </div>
                    {/if}
                </div>
            </div>
        </div>
    </div>
{/if}

<style>
    .modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        backdrop-filter: blur(4px);
    }

    .modal-content {
        background: var(--color-secondary-bg, #1a1a2e);
        border: 1px solid var(--color-border, #333);
        border-radius: 12px;
        width: 90%;
        max-width: 440px;
        max-height: 80vh;
        overflow: hidden;
        display: flex;
        flex-direction: column;
    }

    .modal-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem 1.25rem;
        border-bottom: 1px solid var(--color-border, #333);
    }

    .modal-title {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--color-text, #fff);
        margin: 0;
    }

    .close-btn {
        background: none;
        border: none;
        color: var(--color-text-secondary, #888);
        cursor: pointer;
        padding: 0.25rem;
        border-radius: 6px;
        transition: all 0.2s;
    }

    .close-btn:hover {
        color: var(--color-text, #fff);
        background: var(--color-border, #333);
    }

    .error-banner {
        padding: 0.75rem 1.25rem;
        background: rgba(239, 68, 68, 0.15);
        border-bottom: 1px solid rgba(239, 68, 68, 0.3);
        color: #ef4444;
        font-size: 0.875rem;
    }

    .modal-body {
        padding: 1.25rem;
        overflow-y: auto;
    }

    .create-list-section {
        margin-bottom: 1rem;
    }

    .create-form {
        display: flex;
        gap: 0.5rem;
    }

    .list-input {
        flex: 1;
        padding: 0.5rem 0.75rem;
        background: var(--color-bg, #0f0f1a);
        border: 1px solid var(--color-border, #333);
        border-radius: 8px;
        color: var(--color-text, #fff);
        font-size: 0.875rem;
        outline: none;
        transition: border-color 0.2s;
    }

    .list-input:focus {
        border-color: var(--color-accent, #f97316);
    }

    .list-input::placeholder {
        color: var(--color-text-secondary, #666);
    }

    .create-btn {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.5rem 0.75rem;
        background: var(--color-accent, #f97316);
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: opacity 0.2s;
        white-space: nowrap;
    }

    .create-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .create-btn:not(:disabled):hover {
        opacity: 0.9;
    }

    .lists-section {
        border-top: 1px solid var(--color-border, #333);
        padding-top: 1rem;
    }

    .loading {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        justify-content: center;
        padding: 1.5rem;
        color: var(--color-text-secondary, #888);
    }

    .empty-text {
        text-align: center;
        color: var(--color-text-secondary, #666);
        padding: 1.5rem;
        font-size: 0.875rem;
    }

    .lists-grid {
        display: flex;
        flex-direction: column;
        gap: 0.375rem;
    }

    .list-item-row {
        display: flex;
        align-items: center;
        gap: 0.375rem;
    }

    .list-item {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.625rem 0.75rem;
        background: var(--color-bg, #0f0f1a);
        border: 1px solid var(--color-border, #333);
        border-radius: 8px;
        color: var(--color-text, #fff);
        cursor: pointer;
        transition: all 0.2s;
        width: 100%;
        text-align: left;
    }

    .list-item:hover:not(:disabled) {
        border-color: var(--color-accent, #f97316);
        background: rgba(249, 115, 22, 0.08);
    }

    .list-item.success {
        border-color: #22c55e;
        background: rgba(34, 197, 94, 0.08);
    }

    .list-item:disabled {
        opacity: 0.7;
        cursor: wait;
    }

    .list-name {
        font-size: 0.9rem;
        font-weight: 500;
    }

    .list-action {
        display: flex;
        align-items: center;
        color: var(--color-text-secondary, #888);
    }

    .list-item:hover .list-action {
        color: var(--color-accent, #f97316);
    }

    .list-item.success .list-action {
        color: #22c55e;
    }

    .view-list-link {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        padding: 0.4rem 0.6rem;
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid rgba(34, 197, 94, 0.25);
        border-radius: 6px;
        color: #22c55e;
        font-size: 0.75rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        white-space: nowrap;
    }

    .view-list-link:hover {
        background: rgba(34, 197, 94, 0.2);
        border-color: rgba(34, 197, 94, 0.4);
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    :global(.animate-spin) {
        animation: spin 1s linear infinite;
    }
</style>
