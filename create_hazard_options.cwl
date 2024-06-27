cwlVersion: v1.2
$graph:
  - class: Workflow
    id: create-hazard-options-workflow
    label: create hazard options
    doc: create hazard options
    requirements:
      NetworkAccess:
        networkAccess: true
    inputs:
      catalog_url:
        type: string
        doc: the catalog
    outputs:
      - id: hazard-options
        type: Directory
        outputSource:
          - get-options/hazard-options
    steps:
      get-options:
        run: "#get-hazard-options"
        in:
          catalog_url: catalog_url
        out:
          - hazard-options
  - class: CommandLineTool
    id: get-hazard-options
    requirements:
        NetworkAccess:
            networkAccess: true
        DockerRequirement:
            dockerPull: public.ecr.aws/z0u8g6n1/eodh_hazard_options:latest
    baseCommand: main.py
    inputs:
        catalog_url:
            type: string
            inputBinding:
                prefix: --catalog_url=
                separate: false
                position: 4
    outputs:
        hazard-options:
            type: Directory
            outputBinding:
                glob: "./asset_output"