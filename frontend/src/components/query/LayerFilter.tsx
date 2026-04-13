import { layerColors } from '../../utils/layerColors'

interface Props {
  layers: string[]
  selected: string[]
  onChange: (layers: string[]) => void
}

export function LayerFilter({ layers, selected, onChange }: Props) {
  const toggle = (layer: string) => {
    onChange(selected.includes(layer) ? selected.filter((item) => item !== layer) : [...selected, layer])
  }

  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {layers.map((layer) => (
        <button
          key={layer}
          onClick={() => toggle(layer)}
          className={`rounded-md border px-3 py-2 text-xs font-semibold ${selected.includes(layer) ? layerColors[layer] : 'border-slate-200 bg-white text-slate-600'}`}
        >
          {layer}
        </button>
      ))}
    </div>
  )
}

