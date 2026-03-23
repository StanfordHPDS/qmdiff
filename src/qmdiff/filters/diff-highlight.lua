-- diff-highlight.lua
--
-- Pandoc/Quarto Lua filter that renders .cm-added / .cm-deleted spans
-- produced by preprocess-criticmarkup.py.
--
-- The content inside these spans has already been parsed by Pandoc,
-- so all special characters are properly handled. We just wrap them
-- in format-appropriate styling.
--
-- Supports: PDF (LaTeX), HTML, DOCX

-- ── configuration ──────────────────────────────────────────────────
-- Override these via YAML metadata if you like:
--   diff-added-color: "0,0,1"    (RGB, 0-1 scale)
--   diff-deleted-color: "1,0,0"

local added_latex_color = "blue"
local deleted_latex_color = "red"

-- ── helpers ────────────────────────────────────────────────────────

local function is_latex()
  return FORMAT:match("latex") or FORMAT:match("pdf")
end

local function is_html()
  return FORMAT:match("html")
end

local function is_docx()
  return FORMAT:match("docx") or FORMAT:match("openxml")
end

--- Splice raw LaTeX around a list of inlines.
--- Uses TeX grouping {…} so content is never a macro argument.
local function latex_wrap(open_tex, inlines, close_tex)
  local result = pandoc.List:new()
  result:insert(pandoc.RawInline("latex", open_tex))
  result:extend(inlines)
  result:insert(pandoc.RawInline("latex", close_tex))
  return result
end

--- Splice raw HTML tags around a list of inlines.
local function html_wrap(open_html, inlines, close_html)
  local result = pandoc.List:new()
  result:insert(pandoc.RawInline("html", open_html))
  result:extend(inlines)
  result:insert(pandoc.RawInline("html", close_html))
  return result
end

-- ── Meta filter: inject LaTeX preamble if needed ───────────────────

function Meta(meta)
  -- Read user-configurable colors
  if meta["diff-added-color"] then
    added_latex_color = pandoc.utils.stringify(meta["diff-added-color"])
  end
  if meta["diff-deleted-color"] then
    deleted_latex_color = pandoc.utils.stringify(meta["diff-deleted-color"])
  end

  if is_latex() then
    local preamble = [[
\usepackage[normalem]{ulem}
\providecommand{\cmadded}[1]{{\color{]] .. added_latex_color .. [[}#1}}
\providecommand{\cmdeleted}[1]{{\color{]] .. deleted_latex_color .. [[}\sout{#1}}}
]]
    local includes = meta["header-includes"]
    if not includes then
      includes = pandoc.MetaList({})
    elseif includes.t ~= "MetaList" then
      includes = pandoc.MetaList({ includes })
    end
    includes:insert(pandoc.MetaBlocks({
      pandoc.RawBlock("latex", preamble)
    }))
    meta["header-includes"] = includes
  end

  return meta
end

-- ── Span filter: style the diff markup ─────────────────────────────

function Span(el)
  local is_added   = el.classes:includes("cm-added")
  local is_deleted = el.classes:includes("cm-deleted")
  local is_highlight = el.classes:includes("cm-highlight")
  local is_comment = el.classes:includes("cm-comment")

  if not (is_added or is_deleted or is_highlight or is_comment) then
    return nil  -- not our span, leave it alone
  end

  -- ── PDF / LaTeX ──────────────────────────────────────────────────
  if is_latex() then
    if is_added then
      -- Blue text in a TeX group (no macro argument issues)
      return latex_wrap(
        "{\\color{" .. added_latex_color .. "}",
        el.content,
        "}"
      )
    elseif is_deleted then
      -- Red strikethrough: use Pandoc's native Strikeout inside a
      -- color group so Pandoc handles the \sout{} serialization
      local result = pandoc.List:new()
      result:insert(pandoc.RawInline("latex",
        "{\\color{" .. deleted_latex_color .. "}"
      ))
      result:insert(pandoc.Strikeout(el.content))
      result:insert(pandoc.RawInline("latex", "}"))
      return result
    elseif is_highlight then
      return latex_wrap("{\\colorbox{yellow}{", el.content, "}}")
    elseif is_comment then
      -- Small gray note inline
      return latex_wrap(
        "{\\color{gray}\\footnotesize [",
        el.content,
        "]}"
      )
    end

  -- ── HTML ─────────────────────────────────────────────────────────
  elseif is_html() then
    if is_added then
      return html_wrap(
        '<ins style="color:#1a6baa;text-decoration:none;'
          .. 'background:rgba(26,107,170,0.1);padding:0 2px;'
          .. 'border-radius:2px;">',
        el.content,
        "</ins>"
      )
    elseif is_deleted then
      return html_wrap(
        '<del style="color:#c0392b;'
          .. 'background:rgba(192,57,43,0.08);padding:0 2px;'
          .. 'border-radius:2px;">',
        el.content,
        "</del>"
      )
    elseif is_highlight then
      return html_wrap(
        '<mark style="background:#fef3cd;padding:0 2px;">',
        el.content,
        "</mark>"
      )
    elseif is_comment then
      return html_wrap(
        '<span style="color:#6c757d;font-size:0.9em;">[',
        el.content,
        "]</span>"
      )
    end

  -- ── DOCX ─────────────────────────────────────────────────────────
  elseif is_docx() then
    if is_added then
      -- Pandoc DOCX custom styles (user can define "Added" style in
      -- reference doc); fallback: just use underline
      return pandoc.Underline(el.content)
    elseif is_deleted then
      return pandoc.Strikeout(el.content)
    end
  end

  return nil
end

-- ── Return filters in correct order ────────────────────────────────
-- Meta must run before Span so preamble is injected first.
return {
  { Meta = Meta },
  { Span = Span },
}
