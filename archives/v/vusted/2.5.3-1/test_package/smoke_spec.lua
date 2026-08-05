describe("vusted smoke", function()
  it("runs inside Neovim", function()
    assert.is.equal(1, 1)
    assert.is.truthy(vim.fn.has("nvim") == 1)
    assert.is.equal("table", type(require("vusted.helper")))
  end)
end)

