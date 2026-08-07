describe("vusted smoke", function()
  it("runs inside Neovim", function()
    assert.is.equal(1, 1)
    assert.is.truthy(vim.fn.has("nvim") == 1)
    assert.is.equal("table", type(require("vusted.helper")))
  end)

  it("exposes lfs.dir entry types", function()
    local lfs = require("lfs")
    local root = vim.fn.tempname()
    assert.is.equal(1, vim.fn.mkdir(root, "p"))
    assert.is.equal(0, vim.fn.writefile({ "vusted" }, root .. "/entry.txt"))

    local found_type
    for name, entry_type in lfs.dir(root) do
      if name == "entry.txt" then
        found_type = entry_type
        break
      end
    end

    vim.fn.delete(root, "rf")
    assert.is.equal("file", found_type)
  end)

  it("returns nil and an error for missing lfs.dir paths", function()
    local lfs = require("lfs")
    local missing = vim.fn.tempname() .. "/missing"

    local ok, iterator, err = pcall(lfs.dir, missing)

    assert.is.truthy(ok)
    assert.is.equal(nil, iterator)
    assert.is.equal("string", type(err))
    assert.is.truthy(#err > 0)
  end)
end)

