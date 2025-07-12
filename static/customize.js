// Utility: Toggle list selection
function toggleSelection(event) {
  event.target.classList.toggle("selected");
}

// Utility: Add item to list safely
function appendListItem(listId, text) {
  const list = document.getElementById(listId);
  if (!list) return;
  const li = document.createElement("li");
  li.textContent = text;
  li.onclick = toggleSelection;
  list.appendChild(li);
}

// ------------------ Add Layer ------------------
function addLayer() {
  const materialInput = document.getElementById("material");
  const thicknessInput = document.getElementById("thickness");
  if (!materialInput || !thicknessInput) return;

  const material = materialInput.value;
  const thickness = thicknessInput.value;

  if (!material || !thickness) {
    alert("Material and thickness are required.");
    return;
  }

  fetch("/add-layer", {
    method: "POST",
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ material, thickness })
  })
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        alert(data.error);
      } else {
        appendListItem("layerList", `${material} - ${thickness} inches`);
        thicknessInput.value = "";
      }
    })
    .catch(err => alert("Server error while adding layer."));
}

// ------------------ Delete Layer ------------------
function deleteLayer() {
  const list = document.getElementById("layerList");
  if (!list) return;
  [...list.children].forEach(li => {
    if (li.classList.contains("selected")) list.removeChild(li);
  });
}

// ------------------ Finalize Product ------------------
function finalizeProduct() {
  fetch("/finalize-product", {
    method: "POST"
  })
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        alert(data.error);
      } else {
        const lastProduct = data.products?.[data.products.length - 1];
        if (lastProduct) {
          const text = lastProduct.map(([m, t]) => `${m} ${t}"`).join(" + ");
          appendListItem("productList", text);
        }
        const layerList = document.getElementById("layerList");
        if (layerList) layerList.innerHTML = "";
      }
    })
    .catch(err => alert("Server error while finalizing product."));
}

// ------------------ Delete Product ------------------
function deleteCustomProduct() {
  const list = document.getElementById("productList");
  if (!list) return;
  [...list.children].forEach(li => {
    if (li.classList.contains("selected")) list.removeChild(li);
  });
}

// ------------------ Add Custom Size ------------------
function addCustomSize() {
  const lengthInput = document.getElementById("length");
  const widthInput = document.getElementById("width");
  if (!lengthInput || !widthInput) return;

  const length = lengthInput.value;
  const width = widthInput.value;

  if (!length || !width) {
    alert("Length and width are required.");
    return;
  }

  fetch("/add-size", {
    method: "POST",
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ length, width })
  })
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        alert(data.error);
      } else {
        appendListItem("customSizeList", `${length} x ${width} inches`);
        lengthInput.value = "";
        widthInput.value = "";
      }
    })
    .catch(err => alert("Server error while adding size."));
}

// ------------------ Delete Custom Size ------------------
function deleteCustomSize() {
  const list = document.getElementById("customSizeList");
  if (!list) return;
  [...list.children].forEach(li => {
    if (li.classList.contains("selected")) list.removeChild(li);
  });
}

// ------------------ Generate Matrix ------------------

function generateMatrix() {
  // Pre-authorize new tab to bypass popup blocker
  const newTab = window.open("", "_blank");

  fetch("/generate")
    .then(res => res.json())
    .then(data => {
      if (data.url) {
        newTab.location.href = data.url;
        alert("Matrix updated in Google Sheet!");
      } else {
        newTab.close();
        alert("Matrix generation failed.");
      }
    })
    .catch(error => {
      newTab.close();
      console.error("Error:", error);
      alert("An error occurred while generating the matrix.");
    });
}

/*function generateMatrix() {
  fetch("/generate")
    .then(res => res.json())
    .then(data => {
      console.log("Generate Response:", data);
      if (data.url) {
        alert("Matrix updated in Google Sheet!");
        const newTab = window.open(data.url, "_blank");
        if (!newTab || newTab.closed || typeof newTab.closed == 'undefined') {
          window.location.href = data.url;
        }
      } else {
        alert("Matrix generation failed or URL missing.");
      }
    })
    .catch(error => {
      console.error("Error:", error);
      alert("An error occurred while generating the matrix.");
    });
}*/


/*// Helper to toggle selection
function toggleSelection(event) {
  event.target.classList.toggle("selected");
}

// ------------------ Add Layer ------------------
function addLayer() {
  const material = document.getElementById("material").value;
  const thickness = document.getElementById("thickness").value;

  if (!material || !thickness) {
    alert("Material and thickness are required.");
    return;
  }

  fetch("/add-layer", {
    method: "POST",
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ material, thickness })
  }).then(res => res.json()).then(data => {
    if (data.error) alert(data.error);
    else {
      const list = document.getElementById("layerList");
      const li = document.createElement("li");
      li.textContent = `${material} - ${thickness} inches`;
      li.onclick = toggleSelection;
      list.appendChild(li);
      document.getElementById("thickness").value = "";
    }
  });
}

// ------------------ Delete Layer ------------------
function deleteLayer() {
  const list = document.getElementById("layerList");
  [...list.children].forEach(li => {
    if (li.classList.contains("selected")) list.removeChild(li);
  });
}

// ------------------ Finalize Product ------------------
function finalizeProduct() {
  fetch("/finalize-product", {
    method: "POST"
  }).then(res => res.json()).then(data => {
    if (data.error) alert(data.error);
    else {
      const list = document.getElementById("productList");
      const lastProduct = data.products[data.products.length - 1];
      const text = lastProduct.map(([m, t]) => `${m} ${t}"`).join(" + ");
      const li = document.createElement("li");
      li.textContent = text;
      li.onclick = toggleSelection;
      list.appendChild(li);
      document.getElementById("layerList").innerHTML = "";
    }
  });
}

// ------------------ Delete Product ------------------
function deleteCustomProduct() {
  const list = document.getElementById("productList");
  [...list.children].forEach(li => {
    if (li.classList.contains("selected")) list.removeChild(li);
  });
}

// ------------------ Add Custom Size ------------------
function addCustomSize() {
  const length = document.getElementById("length").value;
  const width = document.getElementById("width").value;

  if (!length || !width) {
    alert("Length and width are required.");
    return;
  }

  fetch("/add-size", {
    method: "POST",
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ length, width })
  }).then(res => res.json()).then(data => {
    if (data.error) alert(data.error);
    else {
      const list = document.getElementById("customSizeList");
      const li = document.createElement("li");
      li.textContent = `${length} x ${width} inches`;
      li.onclick = toggleSelection;
      list.appendChild(li);
      document.getElementById("length").value = "";
      document.getElementById("width").value = "";
    }
  });
}

// ------------------ Delete Custom Size ------------------
function deleteCustomSize() {
  const list = document.getElementById("customSizeList");
  [...list.children].forEach(li => {
    if (li.classList.contains("selected")) list.removeChild(li);
  });
}

// ------------------ Generate Matrix ------------------

function generateMatrix() {
  fetch("/generate")
    .then(res => res.json())
    .then(data => {
      console.log("Generate Response:", data);
      if (data.url) {
        alert("Matrix updated in Google Sheet!");
        // Open the link in a new tab (popup blockers may block this)
        const newTab = window.open(data.url, "_blank");
        if (!newTab || newTab.closed || typeof newTab.closed == 'undefined') {
          // Fallback: redirect in same tab
          window.location.href = data.url;
        }
      } else {
        alert("Matrix generation failed or URL missing.");
      }
    })
    .catch(error => {
      console.error("Error:", error);
      alert("An error occurred while generating the matrix.");
    });
}
*/
