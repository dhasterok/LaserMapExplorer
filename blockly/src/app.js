// Import Blockly core.
import * as Blockly from 'blockly/core';
import * as BlockDynamicConnection from '@blockly/block-dynamic-connection';
// Import a message file.
import * as En from 'blockly/msg/en';
import 'blockly/blocks';  // Import default blocks
import {pythonGenerator} from 'blockly/python';
import { sample_ids, setBaseDir } from './globals';
import './custom_blocks';  // Import custom blocks
import './python_generators';  // Import python generators
import './helper_functions';  // Import helper functions

Blockly.setLocale(En);  // Set the locale to English

// Inject the Blockly workspace and configure it with the dynamic connection plugin
var workspace = Blockly.inject('blocklyDiv', {
    toolbox: document.getElementById('toolbox'), // Your toolbox configuration
    plugins: {
        connectionPreviewer: BlockDynamicConnection.decoratePreviewer(
            Blockly.InsertionMarkerPreviewer // Default previewer enhanced with dynamic connections
        ),
    },
});

// Add a change listener to finalize connections dynamically when blocks are removed or rearranged
workspace.addChangeListener(BlockDynamicConnection.finalizeConnections);

window.workspace = workspace;
window.Blockly = Blockly
new QWebChannel(qt.webChannelTransport, function(channel) {
    window.blocklyBridge = channel.objects.blocklyBridge;
      // Set baseDir from Python by calling a method
    window.blocklyBridge.getBaseDir().then((dir) => {
        setBaseDir(dir);
    });
    window.blocklyBridge.callSetStyleWidgets = function(plotType, callback) {
        window.blocklyBridge.invokeSetStyleWidgets(plotType, function(response) {
            callback(JSON.parse(response));  // Parse the response from Python as a JSON object
        });
    };
    function sendCodeToPython() {
        // Generate Python code from Blockly
        var code = pythonGenerator.workspaceToCode(workspace);
        
        // Send the code to Python via WebChannel
        if (window.blocklyBridge) {
            window.blocklyBridge.runCode(code);
        } else {
            console.log("No blocklyBridge available.");
        }
    }

    function executeBlocks(startBlock) {
        let block = startBlock;
        let code = '';
        //while (block) {
            // Ensure the Python generator is initialized for this workspace
            pythonGenerator.init(workspace);
            // Generate code for the block
            code = pythonGenerator.blockToCode(block) ;
            //block = block.getNextBlock();  // Move to the next block
        //}
        return code;
    }
    // Add a double-click listener for executing blocks
    workspace.addChangeListener(function(event) {
            if (event instanceof Blockly.Events.Click) {
                // Detect double click
                if (workspace.doubleClickPid_) {
                    clearTimeout(workspace.doubleClickPid_);
                    workspace.doubleClickPid_ = undefined;

                    // If the same block is clicked twice
                    if (event.blockId === workspace.doubleClickBlock_) {
                        var block = workspace.getBlockById(workspace.doubleClickBlock_);
                        if (block) {
                            // Execute the block and connected blocks
                            const code = executeBlocks(block);

                            // Send the generated code to Python
                            if (window.blocklyBridge) {
                                window.blocklyBridge.executeCode(code);
                            } else {
                                console.log("No blocklyBridge available.");
                            }
                        }
                        return;
                    }
                }

                // If this is the first click
                if (!workspace.doubleClickPid_) {
                    workspace.doubleClickBlock_ = event.blockId;
                    workspace.doubleClickPid_ = setTimeout(function() {
                        workspace.doubleClickPid_ = undefined;
                    }.bind(workspace), 500);  // Wait 500ms to detect a second click
                }
            }
        });
    workspace.addChangeListener(sendCodeToPython);
    
});

function resizeBlocklyWorkspace() {
    const blocklyDiv = document.getElementById('blocklyDiv');
    Blockly.svgResize(window.workspace);
}

resizeBlocklyWorkspace();