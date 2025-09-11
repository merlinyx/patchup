import React from 'react';

import '../lib/instructions.css';

const StepByStepInstructions = ({ instructions, dpi }) => {
  if (!instructions || !Array.isArray(instructions)) {
    return <div className="instructions-container">No instructions available</div>;
  }

  return (
    <div className="instructions-container">
      <h2>Packing Instructions</h2>
      
      <div className="supplies-section">
        <h2>Supplies Needed</h2>
        <ul>
          <li>Sewing machine or needles</li>
          <li>Threads</li>
          <li>Scissors</li>
          <li>Iron</li>
          <li>Ironing mat or board</li>
          <li>Ruler</li>
          <li>Seam ripper (optional)</li>
          <li>Clips (optional)</li>
          <li>Cutting board (optional)</li>
          <li>Rotary cutter (optional)</li>
        </ul>
      </div>

      {instructions.map((instruction, index) => (
        <div key={index} className="instruction-step">
          <h3>Step {instruction.step}</h3>
          <div className="used-fabrics">
            <p>Prepare the following fabrics for this step (fabric sizes aren't to scale):</p>
            <div className="fabric-images">
              {instruction.used_fabrics.map((fabric, i) => (
                <div key={i} className="fabric-item">
                  <img 
                    src={`data:image/png;base64,${fabric.image}`} 
                    alt={`Fabric ${i}`}
                  />
                  <p>Fabric {fabric.order + 1} ({(fabric.size[0] / dpi).toFixed(2)} x {(fabric.size[1] / dpi).toFixed(2)} in.)
                  {/* {fabric.rotated && Math.min(...fabric.size) / Math.max(...fabric.size) < 0.95 ? `(rotated)` : ``} */}
                  </p>
                </div>
              ))}
              {instruction.packed_fabric && <div key={instruction.used_fabrics.length} className="fabric-item">
                <img 
                  src={`data:image/png;base64,${instruction.packed_fabric}`} 
                  alt={`Packed fabric`}
                />
                <p>Packed fabric ({(instruction.packed_fabric_size[0]/dpi).toFixed(2)} x {(instruction.packed_fabric_size[1]/dpi).toFixed(2)} in.)</p>
              </div>}
            </div>
          </div>
          <div className="strip-images">
            { instruction.strip_images.before_crop && (
            <div className="strip-before-crop">
              <p>Stack fabrics as illustrated below and ensure all edges are properly aligned, then trim along the red dotted line shown in the diagram.</p>
              <img 
                src={`data:image/png;base64,${instruction.strip_images.before_crop}`} 
                alt="Strip before crop"
              />
            </div> )}
            {instruction.trimming_records && instruction.trimming_records.length > 0 && (
              <div className="trimming-records">
                <p>Note: The following fabrics will be trimmed, and the remaining pieces will be saved for later use:</p>
                <div className="trimming-images">
                  {instruction.trimming_records.map((record, i) => (
                    <div key={i} className="trimming-record">
                      <div className="original-fabric">
                        <img 
                          src={`data:image/png;base64,${record.original_image}`} 
                          alt={`Original fabric ${record.fabric_id + 1}`}
                        />
                        <p>Original Fabric {record.fabric_id + 1}</p>
                      </div>
                      <div className="trimmed-fabric">
                        <img 
                          src={`data:image/png;base64,${record.trimmed_image}`} 
                          alt={`Remaining fabric ${record.fabric_id + 1}`}
                        />
                        <p>Remaining piece (will be saved)</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="strip-after-crop">
              <p>{instruction.strip_images.before_crop ? `After trimming, y` : `Stack fabrics as illustrated below and ensure all edges are properly aligned. Y`}ou should have a neat strip like this:</p>
              <img 
                src={`data:image/png;base64,${instruction.strip_images.after_crop}`} 
                alt="Strip after crop"
              />
              <p>The trimmed strip should be ({(instruction.strip_images.after_crop_size[0]/dpi).toFixed(2)} x {(instruction.strip_images.after_crop_size[1]/dpi).toFixed(2)} in.)</p>
              <p>Stitch using a straight seam with quarter inch seam allowance and press seams open to create a flat strip.</p>
            </div>
          </div> 
          <div className="final-result">
            { instruction.packed_fabric && <p className="attachment-instruction">{instruction.attachment_instruction}</p> }
            { instruction.final_before_crop && (
              <img 
                src={`data:image/png;base64,${instruction.final_before_crop}`} 
                alt="Final result before trimming"
              />
            )}
            <p>{instruction.final_before_crop ? `After trimming any extra materials, ` : `And `}the final packed result ({(instruction.final_result_size[0]/dpi).toFixed(2)} x {(instruction.final_result_size[1]/dpi).toFixed(2)} in.) looks like:</p>
            <img 
              src={`data:image/png;base64,${instruction.final_result}`} 
              alt="Final result"
            />
          </div>
        </div>
      ))}
    </div>
  );
};

const StripFirstInstructions = ({ instructions, dpi }) => {
  if (!instructions || !Array.isArray(instructions)) {
    return <div className="instructions-container">No instructions available</div>;
  }

  return (
    <div className="instructions-container">
      <h2>Packing Instructions</h2>
      
      <div className="supplies-section">
        <h2>Supplies Needed</h2>
        <ul>
          <li>Sewing machine or needles</li>
          <li>Threads</li>
          <li>Scissors</li>
          <li>Iron</li>
          <li>Ironing mat or board</li>
          <li>Ruler</li>
          <li>Seam ripper (optional)</li>
          <li>Clips (optional)</li>
          <li>Cutting board (optional)</li>
          <li>Rotary cutter (optional)</li>
        </ul>
      </div>

      <div className="strip-section">
        <h2>Strip Preparation</h2>
        {instructions.map((instruction, index) => (
          <div key={index} className="instruction-step">
            <h3>Strip {instruction.step}</h3>
            <div className="used-fabrics">
              <p>Prepare the following fabrics for this strip (fabric sizes aren't to scale):</p>
              <div className="fabric-images">
                {instruction.used_fabrics.map((fabric, i) => (
                  <div key={i} className="fabric-item">
                    <img 
                      src={`data:image/png;base64,${fabric.image}`} 
                      alt={`Fabric ${i}`}
                    />
                    <p>Fabric {fabric.order + 1} ({(fabric.size[0] / dpi).toFixed(2)} x {(fabric.size[1] / dpi).toFixed(2)} in.)
                    {/* {fabric.rotated && Math.min(...fabric.size) / Math.max(...fabric.size) < 0.95 ? `(rotated)` : ``} */}
                    </p>
                  </div>
                ))}
              </div>
            </div>
            <div className="strip-images">
              { instruction.strip_images.before_crop && (
              <div className="strip-before-crop">
                <p>Stack fabrics as illustrated below and ensure all edges are properly aligned, then trim along the red dotted line shown in the diagram.</p>
                <img 
                  src={`data:image/png;base64,${instruction.strip_images.before_crop}`} 
                  alt="Strip before crop"
                />
              </div> )}
              {instruction.trimming_records && instruction.trimming_records.length > 0 && (
                <div className="trimming-records">
                  <p>Note: The following fabrics will be trimmed, and the remaining pieces will be saved for later use:</p>
                  <div className="trimming-images">
                    {instruction.trimming_records.map((record, i) => (
                      <div key={i} className="trimming-record">
                        <div className="original-fabric">
                          <img 
                            src={`data:image/png;base64,${record.original_image}`} 
                            alt={`Original fabric ${record.fabric_id + 1}`}
                          />
                          <p>Original Fabric {record.fabric_id + 1}</p>
                        </div>
                        <div className="trimmed-fabric">
                          <img 
                            src={`data:image/png;base64,${record.trimmed_image}`} 
                            alt={`Remaining fabric ${record.fabric_id + 1}`}
                          />
                          <p>Remaining piece (will be saved)</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div className="strip-after-crop">
                <p>{instruction.strip_images.before_crop ? `After trimming, y` : `Stack fabrics as illustrated below and ensure all edges are properly aligned. Y`}ou should have a neat strip like this:</p>
                <img 
                  src={`data:image/png;base64,${instruction.strip_images.after_crop}`} 
                  alt="Strip after crop"
                />
                <p>The trimmed strip should be ({(instruction.strip_images.after_crop_size[0]/dpi).toFixed(2)} x {(instruction.strip_images.after_crop_size[1]/dpi).toFixed(2)} in.)</p>
                <p>Stitch using a straight seam with quarter inch seam allowance and press seams open to create a flat strip.</p>
              </div>
            </div> 
          </div>
        ))}
      </div>
      <div className="final-result-section">
        <h2>Strip Assembly</h2>
        {instructions.map((instruction, index) => (
          <div key={index} className="instruction-step">
            <h3>Step {instruction.step}</h3>
            <div className="final-result">
              { instruction.packed_fabric && <p className="attachment-instruction">{instruction.attachment_instruction}</p> }
              { instruction.final_before_crop && (
                <img 
                  src={`data:image/png;base64,${instruction.final_before_crop}`} 
                  alt="Final result before trimming"
                />
              )}
              <p>{instruction.final_before_crop ? `After trimming any extra materials, ` : `And `}the final packed result ({(instruction.final_result_size[0]/dpi).toFixed(2)} x {(instruction.final_result_size[1]/dpi).toFixed(2)} in.) looks like:</p>
              <img 
                src={`data:image/png;base64,${instruction.final_result}`} 
                alt="Final result"
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export { StepByStepInstructions, StripFirstInstructions };
