import { useState } from 'react';
import { ChevronDown, Search, SlidersHorizontal, X } from 'lucide-react';

import type {
  DiscoverCapabilities,
  DiscoverFilterOptions,
  DiscoverFilters,
  DiscoverOption,
} from '../types';


interface DiscoverFiltersBarProps {
  mediaType: string;
  capabilities: DiscoverCapabilities | null;
  options: DiscoverFilterOptions;
  filters: DiscoverFilters;
  onChange(filters: DiscoverFilters): void;
  onReset(): void;
}

function supports(capabilities: DiscoverCapabilities | null, filter: string) {
  return capabilities?.filters.includes(filter) ?? filter === 'search';
}

function setSingle(filters: DiscoverFilters, key: keyof DiscoverFilters, value: string) {
  const next = { ...filters };
  if (value) Object.assign(next, { [key]: value });
  else delete next[key];
  return next;
}

function FilterSelect({ label, value, options, onChange }: {
  label: string;
  value: string;
  options: DiscoverOption[];
  onChange(value: string): void;
}) {
  return (
    <label className="discover-filter-field">
      <span>{label}</span>
      <span className="discover-select-wrap">
        <select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}>
          <option value="">Any</option>
          {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
        <ChevronDown aria-hidden="true" />
      </span>
    </label>
  );
}

export function DiscoverFiltersBar({ mediaType, capabilities, options, filters, onChange, onReset }: DiscoverFiltersBarProps) {
  const [tagsOpen, setTagsOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const selectedTaxonomy = [...(filters.genres ?? []), ...(filters.tags ?? [])];
  const years = Array.from({ length: new Date().getFullYear() - 1898 }, (_, index) => new Date().getFullYear() + 1 - index);

  function toggleTaxonomy(kind: 'genres' | 'tags', value: string) {
    const current = filters[kind] ?? [];
    const next = current.includes(value) ? current.filter((item) => item !== value) : [...current, value];
    onChange({ ...filters, [kind]: next });
  }

  return (
    <div className="discover-filter-shell">
      <div className="discover-filter-grid">
        <label className="discover-filter-field discover-search-filter">
          <span>Search</span>
          <span className="discover-search-input">
            <Search aria-hidden="true" />
            <input
              type="search"
              aria-label="Search catalog"
              value={filters.search ?? ''}
              onChange={(event) => onChange(setSingle(filters, 'search', event.target.value))}
            />
          </span>
        </label>

        {supports(capabilities, 'genres') && (
          <div className="discover-filter-field discover-taxonomy-filter">
            <span>Genres &amp; Tags</span>
            <button type="button" className="discover-filter-button" aria-label="Genres & Tags" aria-expanded={tagsOpen} onClick={() => setTagsOpen((open) => !open)}>
              <span>{selectedTaxonomy.length ? `${selectedTaxonomy.length} selected` : 'Any'}</span>
              <ChevronDown aria-hidden="true" />
            </button>
            {tagsOpen && (
              <div className="discover-taxonomy-menu">
                <strong>Genres</strong>
                <div>{options.genres.map((option) => (
                  <label key={option.value}><input type="checkbox" checked={(filters.genres ?? []).includes(option.value)} onChange={() => toggleTaxonomy('genres', option.value)} />{option.label}</label>
                ))}</div>
                <strong>Tags</strong>
                <div>{options.tags.map((option) => (
                  <label key={option.value}><input type="checkbox" checked={(filters.tags ?? []).includes(option.value)} onChange={() => toggleTaxonomy('tags', option.value)} />{option.label}</label>
                ))}</div>
              </div>
            )}
          </div>
        )}

        {supports(capabilities, 'year') && (
          <FilterSelect label="Year" value={filters.year ? String(filters.year) : ''} options={years.map((year) => ({ value: String(year), label: String(year) }))} onChange={(value) => onChange({ ...setSingle(filters, 'year', value), year: value ? Number(value) : undefined })} />
        )}
        {supports(capabilities, 'season') && (
          <FilterSelect label="Season" value={filters.season ?? ''} options={['WINTER', 'SPRING', 'SUMMER', 'FALL'].map((value) => ({ value, label: value[0] + value.slice(1).toLocaleLowerCase() }))} onChange={(value) => onChange(setSingle(filters, 'season', value))} />
        )}
        {supports(capabilities, 'formats') && (
          <FilterSelect label="Format" value={filters.formats?.[0] ?? ''} options={options.formats} onChange={(value) => onChange({ ...filters, formats: value ? [value] : [] })} />
        )}
        {supports(capabilities, 'statuses') && (
          <FilterSelect label={mediaType === 'anime' ? 'Airing Status' : 'Publishing Status'} value={filters.statuses?.[0] ?? ''} options={options.statuses} onChange={(value) => onChange({ ...filters, statuses: value ? [value] : [] })} />
        )}

        {capabilities?.supportsAdvanced && (
          <button type="button" className={advancedOpen ? 'discover-more-filters active' : 'discover-more-filters'} aria-label="More filters" aria-expanded={advancedOpen} onClick={() => setAdvancedOpen((open) => !open)}>
            {advancedOpen ? <X aria-hidden="true" /> : <SlidersHorizontal aria-hidden="true" />}
          </button>
        )}
      </div>

      {advancedOpen && (
        <section className="discover-advanced-filters" aria-label="Advanced filters">
          {supports(capabilities, 'country') && <FilterSelect label="Country of origin" value={filters.country ?? ''} options={options.countries} onChange={(value) => onChange(setSingle(filters, 'country', value))} />}
          {supports(capabilities, 'source') && <FilterSelect label="Source material" value={filters.source ?? ''} options={options.sources} onChange={(value) => onChange(setSingle(filters, 'source', value))} />}
          {supports(capabilities, 'streaming') && <FilterSelect label="Streaming on" value={filters.streaming ?? ''} options={options.streaming} onChange={(value) => onChange(setSingle(filters, 'streaming', value))} />}
          {supports(capabilities, 'sort') && <FilterSelect label="Sort" value={filters.sort ?? 'popularity'} options={options.sorts} onChange={(value) => onChange(setSingle(filters, 'sort', value || 'popularity'))} />}
          <button type="button" className="discover-reset-filters" onClick={onReset}>Reset all filters</button>
        </section>
      )}

      {selectedTaxonomy.length > 0 && (
        <div className="discover-active-filters" aria-label="Active genres and tags">
          {selectedTaxonomy.map((value) => <span key={value}>{value}</span>)}
        </div>
      )}
    </div>
  );
}
